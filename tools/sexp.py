"""Minimal S-expression reader/writer for KiCad files."""
import re

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError('parse error at %d' % pos)
        pos = m.end()
        lp, rp, s, a = m.groups()
        if lp:
            stack.append([])
        elif rp:
            x = stack.pop()
            stack[-1].append(x)
        elif s is not None:
            stack[-1].append(s[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        elif a is not None:
            stack[-1].append(Sym(a))
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def _atom(x):
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        s = ('%.4f' % x).rstrip('0').rstrip('.')
        return s if s not in ('-0', '') else '0'
    return '"' + str(x).replace('\\', '\\\\').replace('"', '\\"') + '"'


def dumps(e, indent=0):
    if not isinstance(e, list):
        return _atom(e)
    if all(not isinstance(c, list) for c in e):
        return '(' + ' '.join(_atom(c) for c in e) + ')'
    pad = '  ' * (indent + 1)
    parts = []
    line = '(' + ' '.join(_atom(c) for c in e if not isinstance(c, list)) if False else None
    out = '('
    first = True
    for c in e:
        if isinstance(c, list):
            out += '\n' + pad + dumps(c, indent + 1)
        else:
            out += ('' if first else ' ') + _atom(c)
        first = False
    return out + ')'


def find(e, key):
    """All direct children lists whose head is key."""
    return [c for c in e if isinstance(c, list) and c and c[0] == key]


def find1(e, key):
    r = find(e, key)
    return r[0] if r else None


def walk(e, key):
    if isinstance(e, list):
        if e and e[0] == key:
            yield e
        for c in e:
            yield from walk(c, key)


def S(*a):
    """Build a list node; first item becomes a bare symbol."""
    return [Sym(a[0])] + list(a[1:])
