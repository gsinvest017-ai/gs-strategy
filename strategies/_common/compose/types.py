"""Parametric port types: the objects of the strategy-graph category.

A port type is written ``Base`` or ``Base[arg, ...]``.  Composition (an edge)
is legal when the producer's type is a *specialisation* of what the consumer
asks for:

* ``Signal[llm]``  -> ``Signal``        ok   (an unparameterised input accepts any arguments)
* ``Signal[llm]``  -> ``Signal[llm]``   ok   (exact match)
* ``Signal[rule]`` -> ``Signal[llm]``   rejected
* ``Signal``       -> ``Signal[llm]``   rejected (the producer promises less than is required)
* ``*`` inside the brackets of an input matches any single argument.

Plain names compare by equality, so every existing graph keeps its meaning.
The UI mirrors this rule in ``graph/ui/src/model.js``; Python stays the
authority (R1).
"""
from __future__ import annotations

from dataclasses import dataclass
import re

_TOKEN = re.compile(r'^([A-Za-z][A-Za-z0-9_]*)(?:\[([A-Za-z0-9_*.,\- ]*)\])?$')


@dataclass(frozen=True)
class Ty:
    base: str
    args: tuple = ()

    @classmethod
    def parse(cls, text):
        if isinstance(text, Ty):
            return text
        match = _TOKEN.match(str(text).strip())
        if not match:
            raise ValueError(f'invalid port type {text!r}')
        args = tuple(a.strip() for a in match.group(2).split(',')) if match.group(2) is not None else ()
        if match.group(2) is not None and (not args or any(not a for a in args)):
            raise ValueError(f'invalid port type {text!r}')
        return cls(match.group(1), args)

    def __str__(self):
        return self.base + (f'[{",".join(self.args)}]' if self.args else '')

    def accepts(self, produced):
        """Is a value of type ``produced`` a legal input for a port of type ``self``?"""
        produced = Ty.parse(produced)
        if produced.base != self.base:
            return False
        if not self.args:
            return True
        if len(self.args) != len(produced.args):
            return False
        return all(want in ('*', got) for want, got in zip(self.args, produced.args))


def compatible(output_type, input_type):
    """Edge rule used by ``Registry.normalize``; malformed types never connect."""
    try:
        return Ty.parse(input_type).accepts(output_type)
    except ValueError:
        return False


def base(type_text):
    return Ty.parse(type_text).base
