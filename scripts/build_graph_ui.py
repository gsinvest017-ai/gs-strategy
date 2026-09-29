"""Build the local graph UI only when its sources or dependencies changed."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    ui = root / 'strategies/_common/graph/ui'
    sources = []
    for directory, folders, filenames in os.walk(ui):
        folders[:] = [name for name in folders if name not in
                      {'node_modules', 'dist', 'coverage', 'test-results'}]
        sources.extend(Path(directory) / name for name in filenames)
    digest = hashlib.sha256()
    for path in sorted(sources):
        digest.update(path.relative_to(ui).as_posix().encode())
        digest.update(path.read_bytes())
    revision = digest.hexdigest()
    stamp = ui / 'dist/.source-hash'
    if (ui / 'dist/index.html').is_file() and stamp.is_file() and stamp.read_text() == revision:
        print('[graph-ui] build 已是最新版本', flush=True)
        return 0
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if npm is None:
        raise SystemExit('graph-ui build 需要 node 與 npm')
    print('[graph-ui] 更新本地 JS、CSS 與字型 build', flush=True)
    # Reproducible install also handles a changed lockfile in an existing checkout.
    subprocess.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=ui, check=True)
    subprocess.run([npm, 'run', 'build', '--', '--logLevel', 'warn'], cwd=ui, check=True)
    stamp.write_text(revision, encoding='ascii')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
