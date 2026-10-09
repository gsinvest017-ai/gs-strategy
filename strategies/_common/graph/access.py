"""Admin-owned, deny-by-default identity and workspace routing.

The trusted proxy MUST strip client copies of both headers, authenticate its
OIDC session, and inject issuer+subject and a private token over loopback.
Policy and token files must be writable only by the trusted administrator.
This is application isolation, not a sandbox for hostile strategy programs.
"""
import hmac
import ipaddress
import json
from pathlib import Path
import re
import threading

from .service import GraphService


class AccessDenied(Exception):
    pass


class WorkspaceServices:
    def __init__(self, policy_path, *, service_factory=GraphService):
        policy_path = Path(policy_path).resolve()
        policy = json.loads(policy_path.read_text(encoding='utf-8'))
        if policy.get('schema') != 'straty-access/1':
            raise ValueError('unsupported access policy')
        self.root = Path(policy['workspace_root']).resolve()
        self.source_root = Path(policy['source_root']).resolve()
        token_path = Path(policy['proxy_token_file'])
        if not token_path.is_absolute():
            token_path = policy_path.parent / token_path
        self.token = token_path.read_text(encoding='utf-8').strip()
        if len(self.token) < 32:
            raise ValueError('proxy token must have at least 32 characters')
        self.principals = policy['principals']
        workspaces = set()
        self.workspace_paths = {}
        for subject, grant in self.principals.items():
            workspace = grant['workspace']
            if not subject or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', workspace):
                raise ValueError('invalid principal or workspace')
            # Reject case aliases even before directories exist. Policy files
            # remain portable between case-sensitive Linux and Windows hosts.
            if workspace.casefold() in workspaces:
                raise ValueError('workspace cannot be shared between principals')
            workspaces.add(workspace.casefold())
            resolved = (self.root / workspace).resolve()
            if resolved == self.root or not resolved.is_relative_to(self.root):
                raise ValueError('workspace must remain below workspace_root')
            for existing in self.workspace_paths.values():
                if resolved.is_relative_to(existing) or existing.is_relative_to(resolved):
                    raise ValueError('resolved workspace cannot be shared or nested between principals')
            self.workspace_paths[subject] = resolved
            for key in ('strategies', 'node_types'):
                if not isinstance(grant.get(key), list) or any(not isinstance(x, str) or not x or x == '*' for x in grant[key]):
                    raise ValueError('explicit strategy and node type grants required')
        self.services = {}
        self.factory = service_factory
        self.lock = threading.Lock()

    def authenticate(self, headers, client_ip):
        if not ipaddress.ip_address(client_ip).is_loopback:
            raise AccessDenied()
        # Reject duplicate security headers instead of trusting first/last wins.
        for name in ('X-Straty-Proxy-Token', 'X-Straty-Subject'):
            if hasattr(headers, 'get_all') and len(headers.get_all(name, [])) != 1:
                raise AccessDenied()
        supplied = headers.get('X-Straty-Proxy-Token', '')
        if not hmac.compare_digest(supplied.encode(), self.token.encode()):
            raise AccessDenied()
        subject = headers.get('X-Straty-Subject', '')
        if subject not in self.principals:
            raise AccessDenied()
        with self.lock:
            # Pin canonical paths at startup; reject later alias replacement.
            for principal, grant in self.principals.items():
                if (self.root / grant['workspace']).resolve() != self.workspace_paths[principal]:
                    raise AccessDenied()
            if subject not in self.services:
                grant = self.principals[subject]
                root = self.workspace_paths[subject]
                self.services[subject] = self.factory(
                    root, owner_subject=subject, allowed_strategies=grant['strategies'],
                    allowed_node_types=grant['node_types'], source_root=self.source_root)
            return subject, self.services[subject]

    def close(self):
        for service in self.services.values():
            if service.active:
                service._token.cancel()
                service._thread.join(timeout=10)
