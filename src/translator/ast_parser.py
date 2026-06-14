from __future__ import annotations

from src.translator.tokenizer import Token, Tokenizer, TokenType


class NumLit:
    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"NumLit({self.value})"


class StrLit:
    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f'StrLit("{self.value}")'


class VarLit:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"VarLit({self.name})"


class Op:
    def __init__(self, op: str, args: list) -> None:
        self.op = op
        self.args = args

    def __repr__(self) -> str:
        return f"Op({self.op}, {self.args})"


class IfExpr:
    def __init__(self, cond: object, then: object, else_: object) -> None:
        self.cond = cond
        self.then = then
        self.else_ = else_

    def __repr__(self) -> str:
        return f"IfExpr({self.cond}, {self.then}, {self.else_})"


class Setq:
    def __init__(self, name: str, value: object) -> None:
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return f"Setq({self.name}, {self.value})"


class Defun:
    def __init__(self, name: str, args: list[str], body: object) -> None:
        self.name = name
        self.args = args
        self.body = body

    def __repr__(self) -> str:
        return f"Defun({self.name}, {self.args}, {self.body})"


class FuncCall:
    def __init__(self, name: str, args: list) -> None:
        self.name = name
        self.args = args

    def __repr__(self) -> str:
        return f"FuncCall({self.name}, {self.args})"


class Print:
    def __init__(self, value: object) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Print({self.value})"


class Read:
    def __repr__(self) -> str:
        return "Read()"


class LoopExpr:
    def __init__(self, var: str, start: object, end: object, body: object) -> None:
        self.var = var
        self.start = start
        self.end = end
        self.body = body

    def __repr__(self) -> str:
        return f"LoopExpr({self.var}, {self.start}, {self.end}, {self.body})"


class Progn:
    def __init__(self, exprs: list) -> None:
        self.exprs = exprs

    def __repr__(self) -> str:
        return f"Progn({self.exprs})"


class ParseError(Exception):
    def __init__(self, msg: str, line: int) -> None:
        super().__init__(f"Parse error on line {line}: {msg}")


class Parser:
    def __init__(self, tokenizer: Tokenizer) -> None:
        self.tokenizer = tokenizer
        self.functions: set[str] = set()
        self.current: Token = self._next()

    def _next(self) -> Token:
        tok = self.tokenizer.get_next_token()
        while tok.token_type == TokenType.SPACE:
            tok = self.tokenizer.get_next_token()
        return tok

    def _advance(self) -> Token:
        tok = self.current
        self.current = self._next()
        return tok

    def _expect(self, token_type: TokenType) -> Token:
        if self.current.token_type != token_type:
            raise ParseError(
                f"expected {token_type.name} but got {self.current.token_type.name}",
                self.current.line,
            )
        return self._advance()

    def parse_expr(self) -> object:
        tok = self.current
        if tok.token_type == TokenType.NUM_LIT:
            self._advance()
            return NumLit(int(tok.value))
        if tok.token_type == TokenType.STR_LIT:
            self._advance()
            return StrLit(tok.value)
        if tok.token_type == TokenType.VAR_LIT:
            self._advance()
            return VarLit(tok.value)
        if tok.token_type == TokenType.L_PAR:
            return self.parse_list()
        raise ParseError(f"unexpected token {tok.token_type.name}", tok.line)

    def parse_list(self) -> object:
        self._expect(TokenType.L_PAR)
        tok = self.current

        if tok.token_type == TokenType.IF:
            return self.parse_if()
        if tok.token_type == TokenType.SETQ:
            return self.parse_setq()
        if tok.token_type == TokenType.DEFUN:
            return self.parse_defun()
        if tok.token_type == TokenType.PRINT:
            return self.parse_print()
        if tok.token_type == TokenType.READ:
            return self.parse_read()
        if tok.token_type == TokenType.LOOP:
            return self.parse_loop()
        if tok.token_type in (
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.MUL,
            TokenType.DIV,
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.GT,
        ):
            return self.parse_op()
        if tok.token_type == TokenType.VAR_LIT:
            name = tok.value
            if name in self.functions:
                return self.parse_funccall()
            self._advance()
            if self.current.token_type == TokenType.R_PAR:
                self._expect(TokenType.R_PAR)
                return VarLit(name)
            args: list = []
            while self.current.token_type != TokenType.R_PAR:
                args.append(self.parse_expr())
            self._expect(TokenType.R_PAR)
            return FuncCall(name, args)

        raise ParseError(f"unknown expression head: {tok.token_type.name}", tok.line)

    def parse_body_exprs(self) -> object:
        exprs: list = []
        while self.current.token_type != TokenType.R_PAR:
            exprs.append(self.parse_expr())
        if len(exprs) == 1:
            return exprs[0]
        return Progn(exprs)

    def parse_if(self) -> IfExpr:
        self._expect(TokenType.IF)
        cond = self.parse_expr()
        then = self.parse_expr()
        else_ = self.parse_expr()
        self._expect(TokenType.R_PAR)
        return IfExpr(cond, then, else_)

    def parse_setq(self) -> Setq:
        self._expect(TokenType.SETQ)
        name = self._expect(TokenType.VAR_LIT).value
        value = self.parse_expr()
        self._expect(TokenType.R_PAR)
        return Setq(name, value)

    def parse_defun(self) -> Defun:
        self._expect(TokenType.DEFUN)
        name = self._expect(TokenType.VAR_LIT).value
        self._expect(TokenType.L_PAR)
        args: list[str] = []
        while self.current.token_type != TokenType.R_PAR:
            args.append(self._expect(TokenType.VAR_LIT).value)
        self._expect(TokenType.R_PAR)
        body = self.parse_body_exprs()
        self._expect(TokenType.R_PAR)
        self.functions.add(name)
        return Defun(name, args, body)

    def parse_print(self) -> Print:
        self._expect(TokenType.PRINT)
        value = self.parse_expr()
        self._expect(TokenType.R_PAR)
        return Print(value)

    def parse_read(self) -> Read:
        self._expect(TokenType.READ)
        self._expect(TokenType.R_PAR)
        return Read()

    def parse_op(self) -> Op:
        op_tok = self._advance()
        op = op_tok.value
        if op_tok.token_type in (TokenType.MINUS, TokenType.DIV):
            left = self.parse_expr()
            right = self.parse_expr()
            self._expect(TokenType.R_PAR)
            return Op(op, [left, right])
        args: list = []
        while self.current.token_type != TokenType.R_PAR:
            args.append(self.parse_expr())
        self._expect(TokenType.R_PAR)
        return Op(op, args)

    def parse_funccall(self) -> FuncCall:
        name = self._expect(TokenType.VAR_LIT).value
        args: list = []
        while self.current.token_type != TokenType.R_PAR:
            args.append(self.parse_expr())
        self._expect(TokenType.R_PAR)
        return FuncCall(name, args)

    def parse_loop(self) -> LoopExpr:
        self._expect(TokenType.LOOP)
        self._expect(TokenType.FOR)
        var = self._expect(TokenType.VAR_LIT).value
        self._expect(TokenType.FROM)
        start = self.parse_expr()
        self._expect(TokenType.TO)
        end = self.parse_expr()
        self._expect(TokenType.DO)
        body = self.parse_body_exprs()
        self._expect(TokenType.R_PAR)
        return LoopExpr(var, start, end, body)

    def parse(self) -> list:
        exprs: list = []
        while self.current.token_type != TokenType.EOF:
            node = self.parse_expr()
            if isinstance(node, Defun):
                self.functions.add(node.name)
            exprs.append(node)
        return exprs

    def pre_scan_functions(self, source: str) -> None:
        """Register defun names before full parse for forward references."""
        import re

        for match in re.finditer(r"\(defun\s+([\w-]+)", source):
            self.functions.add(match.group(1))
