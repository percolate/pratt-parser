"""
a Pratt parser (and interpreter) for simple arithmetic expressions
"""
from __future__ import unicode_literals, absolute_import

import operator
import math
from . import lexer

OP_REGISTRY = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.div,
    "^": operator.pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": lambda x: math.log(x, 2)
}


class ParserError(Exception):
    pass


class Symbol(object):
    """Base class for all nodes"""
    id = None
    lbp = 0

    def __init__(self, parser, value=None):
        self.parser = parser
        self.value = value or self.id
        self.first = None
        self.second = None

    def nud(self):
        raise ParserError("Symbol action undefined for `%s'" % self.value)

    def led(self, left):
        raise ParserError("Infix action undefined for `%s'" % self.value)

    def eval(self, doc):
        raise ParserError("Unimplemented")

    def __repr__(self):
        return "<'%s'>" % self.value


class Literal(Symbol):
    """Simple literal (a number or a variable/function name)
       just produces itself"""
    def nud(self):
        return self


class Infix(Symbol):
    """Infix operator"""
    rightAssoc = False

    def led(self, left):
        self.first = left
        rbp = self.lbp - int(self.rightAssoc)
        self.second = self.parser.expression(rbp)
        return self

    def eval(self, doc):
        return OP_REGISTRY[self.value](
            self.first.eval(doc),
            self.second.eval(doc)
        )

    def __repr__(self):
        return "<'%s'>(%s, %s)" % (
            self.value, repr(self.first), repr(self.second)
        )


class InfixR(Infix):
    """Infix (right associative) operator"""
    rightAssoc = True


class Prefix(Symbol):
    """Prefix operator.
       For the sake of simplicity has fixed right binding power"""
    def nud(self):
        self.first = self.parser.expression(80)
        return self

    def eval(self, doc):
        return OP_REGISTRY[self.value](self.first)

    def __repr__(self):
        return "<'%s'>(%s)" % (
            self.value, repr(self.first)
        )


class Parser(object):
    """
    Main parser class. Contains both the grammar definition
    and a pointer to the current token stream
    """
    def __init__(self, lex=lexer.lex):
        self.lex = lex
        self.symbol_table = {}
        self.define("<end>")

        self.tokens = iter(())
        self.token = None

    def define(self, sid, bp=0, symbol_class=Symbol):
        symbol_table = self.symbol_table
        sym = symbol_table[sid] = type(
            symbol_class.__name__,
            (symbol_class,),
            {'id': sid, 'lbp': bp}
        )

        def wrapper(val):
            val.id = sid
            val.lbp = sym.lbp
            symbol_table[sid] = val
            return val

        return wrapper

    def expression(self, rbp):
        tok = self.token
        self.advance()
        left = tok.nud()
        while rbp < self.token.lbp:
            tok = self.token
            self.advance()
            left = tok.led(left)
        return left

    def advance(self, value=None):
        tok = self.token
        if value and value not in (tok.value, tok.id):
            raise ParserError(
                "Expected `%s'; got `%s' instead" % (value, self.token.value))
        try:
            tok = self.tokens.next()
            symbol_table = self.symbol_table
            # first look up symbol's value
            if tok.value in symbol_table:
                sym = symbol_table[tok.value]
            elif tok.token_type in symbol_table:
                # then symbol's type
                sym = symbol_table[tok.token_type]
            else:
                raise ParserError("Undefined token %s" % repr(tok))
            self.token = sym(self, tok.value)
        except StopIteration:
            self.token = self.symbol_table["<end>"](self)

        return self.token

    def parse(self, source):
        try:
            self.tokens = self.lex(source)
            self.advance()
            return self.expression(0)
        finally:
            self.tokens = iter(())
            self.token = None


"""
Grammar definition:

expression ::= mul-expr ( ( '+' | '-' ) mul-expr )*
mul-expr ::= pow-expr ( ( '*' | '/' ) pow-expr )*
pow-expr ::= prefix-expr ['^' pow-expr]
prefix-expr ::= [ '-' ] primary
primary ::= '(' expr ')' | number | name [ '(' expr ( ',' expr )* ')' ]
"""

expr = Parser()
# just to leave ourselves some space, start with 50
expr.define("+", 50, Infix)
expr.define("*", 60, Infix)
expr.define("/", 60, Infix)
expr.define("^", 70, InfixR)


@expr.define("<number>")
class Number(Literal):
    """Only defined for the sake of eval"""
    def eval(self, doc):
        return float(self.value)


@expr.define("<name>")
class Reference(Literal):
    """Only defined for the sake of eval"""
    def eval(self, doc):
        try:
            return doc[self.value]
        except KeyError:
            raise ParserError("Missing reference '%s'" % self.value)


@expr.define("-", 50)
class Minus(Infix, Prefix):
    """This combines both Prefix' nud and Infix' led"""
    def eval(self, doc):
        if self.second is None:
            return operator.neg(self.first.eval(doc))
        return super(Minus, self).eval(doc)

expr.define(",")
expr.define(")")


@expr.define("(", 90)
class FunctionCall(Symbol):
    """Defining both function application and parenthesized expression"""
    def nud(self):
        p = self.parser
        e = p.expression(0)
        p.advance(")")
        return e

    def led(self, left):
        self.first = left
        args = self.second = []
        p = self.parser
        while p.token.value != ")":
            args.append(p.expression(0))
            if p.token.value != ",":
                break
            p.advance(",")
        p.advance(")")
        return self

    def __repr__(self):
        return "<Call:'%s'>(%s)>" % (
            self.first.value,
            ', '.join(map(repr, self.second))
        )

    def eval(self, doc):
        try:
            return OP_REGISTRY[self.first.value](
                *(val.eval(doc) for val in self.second)
            )
        except KeyError as e:
            raise ParserError("Invalid function '%s'" % e.args[0])


