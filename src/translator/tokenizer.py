from __future__ import annotations

import enum
from collections.abc import Callable
from functools import partial
from io import SEEK_SET, TextIOBase


class TokenParseError(Exception):
    def __init__(self, msg: str = "Failed while parsing token") -> None:
        super().__init__(msg)


def parse_keyword(keyword: str, text: TextIOBase) -> str:
    s = text.read(len(keyword))
    if s == keyword:
        return keyword
    return ""


def parse_space(text: TextIOBase) -> str:
    start = text.read(1)
    if start == " ":
        pos = text.tell()
        cur = text.read(1)
        while cur == " ":
            pos = text.tell()
            cur = text.read(1)
        text.seek(pos, SEEK_SET)
        return " "
    return ""


def parse_num(text: TextIOBase) -> str:
    pos = text.tell()
    cur = text.read(1)
    if cur not in "0123456789-" and cur != "-":
        return ""
    if cur == "-":
        nxt = text.read(1)
        if not nxt.isdecimal():
            text.seek(pos, SEEK_SET)
            return ""
        res = "-" + nxt
    else:
        res = cur
    p = text.tell()
    cur = text.read(1)
    while cur.isdecimal():
        res += cur
        p = text.tell()
        cur = text.read(1)
    text.seek(p, SEEK_SET)
    return res


def parse_string(text: TextIOBase) -> str:
    start = text.read(1)
    if start != '"':
        return ""
    res = ""
    cur = text.read(1)
    while cur and cur != '"':
        res += cur
        cur = text.read(1)
    return res if cur == '"' else ""


def parse_var(text: TextIOBase) -> str:
    res = ""
    cur = text.read(1)
    if cur.isalpha() or cur == "_":
        res += cur
        pos = text.tell()
        cur = text.read(1)
        while cur.isalnum() or cur in "_-":
            res += cur
            pos = text.tell()
            cur = text.read(1)
        text.seek(pos, SEEK_SET)
    return res


@enum.unique
class TokenType(enum.Enum):
    IF = ("if",)
    LOOP = ("loop",)
    FOR = ("for",)
    FROM = ("from",)
    TO = ("to",)
    DO = ("do",)
    SETQ = ("setq",)
    DEFUN = ("defun",)
    READ = ("read",)
    PRINT = ("print",)

    L_PAR = ("(",)
    R_PAR = (")",)
    SPACE = (None, parse_space)

    NEQ = ("/=",)
    EQ = ("=",)
    GT = (">",)
    LT = ("<",)
    PLUS = ("+",)
    MINUS = ("-",)
    MUL = ("*",)
    DIV = ("/",)

    NUM_LIT = (None, parse_num)
    STR_LIT = (None, parse_string)
    VAR_LIT = (None, parse_var)

    EOF = ("",)

    def __init__(self, keyword: str | None, rule: Callable[[TextIOBase], str] | None = None):
        if keyword is None:
            assert rule is not None
            self._rule = rule
        else:
            self._rule = partial(parse_keyword, keyword)


class Token:
    def __init__(self, token_type: TokenType, value: str, line: int) -> None:
        self.token_type = token_type
        self.value = value
        self.line = line


class Tokenizer:
    def __init__(self, text: TextIOBase) -> None:
        self.text = text
        self.line = 1

    def get_next_token(self) -> Token:
        for token_type in TokenType:
            pos = self.text.tell()
            val = token_type._rule(self.text)
            if val != "":
                return Token(token_type, val, self.line)
            self.text.seek(pos, SEEK_SET)

        cur = self.text.read(1)
        if cur == "":
            return Token(TokenType.EOF, "", self.line)
        if cur == "\n":
            self.line += 1
            return self.get_next_token()
        if cur.isspace():
            return self.get_next_token()
        msg = f"Unexpected character: {cur!r} at line {self.line}"
        raise TokenParseError(msg)
