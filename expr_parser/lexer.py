"""
A simple demo lexer for a pratt parser
"""
from __future__ import absolute_import, unicode_literals

import re

TOKENS = (
    ('ws', r'\s+'),
    ('name', r'[a-z][\w_]*'),
    ('infix', r'[+\-*/\^]'),
    ('punct', r'[\(\),]'),
    ('number', r'(:?\d*\.)?\d+'),
)


TOKEN_RE = '|'.join(
    "(?P<%s>%s)" % t for t in TOKENS
)

LEX_RE = re.compile(TOKEN_RE, re.UNICODE | re.VERBOSE | re.IGNORECASE)


class LexerException(Exception):
    pass


class Token(object):
    def __init__(self, token_type, value, pos):
        self.token_type = token_type
        self.value = value
        self.pos = pos

    def __repr__(self):
        return "%s('%s', %d)" % (self.token_type, self.value, self.pos)

    def __str__(self):
        return repr(self)


def lex(source, pat=LEX_RE):
    i = 0

    def error():
        raise LexerException(
            "Unexpected character at position %d: `%s`" % (i, source[i])
        )
    for m in pat.finditer(source):
        pos = m.start()
        if pos > i:
            error()
        i = m.end()
        name = m.lastgroup
        if name == "ws":
            continue
        else:
            token_type = "<%s>" % name
            t = Token(token_type, m.group(0), pos)
        yield t

    if i < len(source):
        error()
