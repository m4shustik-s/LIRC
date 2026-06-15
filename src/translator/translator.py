from __future__ import annotations

from src.config import IOMemoryMapping
from src.translator.ast_parser import (
    Defun,
    FuncCall,
    IfExpr,
    LoopExpr,
    NumLit,
    Op,
    Print,
    Progn,
    Read,
    Setq,
    StrLit,
    VarLit,
)

OUT_ADDR = IOMemoryMapping.OUT.value
IN_CTRL = IOMemoryMapping.IN_CTRL.value
IN_ADDR = IOMemoryMapping.IN.value


class Translator:
    def __init__(self) -> None:
        self.code: list[str] = []
        self.globals: dict[str, int] = {}
        self.functions: dict[str, str] = {}
        self.var_offset = 0x400
        self.data_offset = 0x100
        self.read_buffer_base = 0x800
        self.strings: dict[str, tuple[str, int]] = {}
        self.string_counter = 0
        self.label_counter = 0
        self.defuns: list[Defun] = []
        self.main_nodes: list = []
        self.string_vars: set[str] = set()
        self.constants: dict[int, int] = {}

    def _emit_num(self, value: int) -> None:
        if -32768 <= value <= 32767:
            self.emit(f"ADDI $v0, $zero, {value}")
            return
        if value not in self.constants:
            self.constants[value] = self.data_offset
            self.data_offset += 4
        self.emit(f"LW $v0, {self.constants[value]}($zero)")

    def _alloc_var(self, name: str) -> int:
        if name not in self.globals:
            self.globals[name] = self.var_offset
            self.var_offset += 4
        return self.globals[name]

    def _alloc_string(self, text: str) -> int:
        label = f"str_{self.string_counter}"
        addr = self.data_offset
        self.strings[label] = (text, addr)
        self.data_offset += 4 * (len(text) + 1)
        self.string_counter += 1
        return addr

    def _make_label(self, prefix: str) -> str:
        label = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def emit(self, instruction: str) -> None:
        self.code.append(instruction)

    def translate(self, ast_nodes: list) -> str:
        self.defuns = [n for n in ast_nodes if isinstance(n, Defun)]
        self.main_nodes = [n for n in ast_nodes if not isinstance(n, Defun)]
        for d in self.defuns:
            self.functions[d.name] = f"fn_{d.name}"

        asm: list[str] = [".text"]
        main_code: list[str] = []
        self.code = main_code
        self.emit("main:")
        self.emit("ADDI $sp, $zero, 4000")
        self.emit("ADDI $gp, $zero, 0")
        for node in self.main_nodes:
            self.compile_stmt(node)
        self.emit("HALT")

        defun_code: list[str] = []
        for d in self.defuns:
            self.code = defun_code
            self._compile_defun(d)

        asm.extend(main_code)
        asm.extend(defun_code)
        if self.strings:
            asm.append("")
            asm.append(".data")
            for label, (val, addr) in self.strings.items():
                asm.append(f"{label}: .pascal \"{val}\"  # @0x{addr:X}")
        if self.constants:
            if not self.strings:
                asm.append("")
                asm.append(".data")
            for const_val, addr in sorted(self.constants.items(), key=lambda item: item[1]):
                asm.append(f"const_{addr:X}: .word {const_val}  # @0x{addr:X}")
        return "\n".join(asm)

    def _compile_defun(self, node: Defun) -> None:
        label = self.functions[node.name]
        self.emit(f"{label}:")
        for i, arg in enumerate(node.args):
            off = self._alloc_var(arg)
            self.emit(f"LW $v0, {4 * (i + 1)}($sp)")
            self.emit(f"SW $v0, {off}($gp)")
        self.compile_expr(node.body)
        self.emit("JR $ra")

    def compile_stmt(self, node: object) -> None:
        self.compile_expr(node)

    def compile_expr(self, node: object) -> None:
        if isinstance(node, NumLit):
            self._emit_num(node.value)
        elif isinstance(node, VarLit):
            if node.name not in self.globals:
                msg = f"Undefined variable: {node.name}"
                raise ValueError(msg)
            self.emit(f"LW $v0, {self.globals[node.name]}($gp)")
        elif isinstance(node, Setq):
            self.compile_expr(node.value)
            off = self._alloc_var(node.name)
            if isinstance(node.value, Read):
                self.string_vars.add(node.name)
            self.emit(f"SW $v0, {off}($gp)")
        elif isinstance(node, IfExpr):
            label_else = self._make_label("if_else")
            label_end = self._make_label("if_end")
            self.compile_expr(node.cond)
            self.emit(f"BEQ $v0, $zero, {label_else}")
            self.compile_expr(node.then)
            self.emit(f"J {label_end}")
            self.emit(f"{label_else}:")
            self.compile_expr(node.else_)
            self.emit(f"{label_end}:")
        elif isinstance(node, Op):
            self._compile_op(node)
        elif isinstance(node, Print):
            self._compile_print(node)
        elif isinstance(node, Read):
            self._compile_read()
        elif isinstance(node, FuncCall):
            self._compile_call(node)
        elif isinstance(node, LoopExpr):
            self._compile_loop(node)
        elif isinstance(node, Progn):
            for expr in node.exprs:
                self.compile_expr(expr)
        else:
            msg = f"Unknown node: {type(node)}"
            raise ValueError(msg)

    def _compile_op(self, node: Op) -> None:
        if not node.args:
            self.emit("ADDI $v0, $zero, 0")
            return
        self.compile_expr(node.args[0])
        for arg in node.args[1:]:
            self.emit("ADDI $sp, $sp, -4")
            self.emit("SW $v0, 0($sp)")
            self.compile_expr(arg)
            self.emit("LW $t0, 0($sp)")
            self.emit("ADDI $sp, $sp, 4")
            if node.op == "+":
                self.emit("ADD $v0, $t0, $v0")
            elif node.op == "-":
                self.emit("SUB $v0, $t0, $v0")
            elif node.op == "*":
                self.emit("MUL $v0, $t0, $v0")
            elif node.op == "/":
                self.emit("DIV $v0, $t0, $v0")
            elif node.op == "<":
                self.emit("SLT $v0, $t0, $v0")
            elif node.op == ">":
                self.emit("SLT $v0, $v0, $t0")
            elif node.op == "=":
                eq_true = self._make_label("eq_true")
                eq_end = self._make_label("eq_end")
                self.emit(f"BEQ $t0, $v0, {eq_true}")
                self.emit("ADDI $v0, $zero, 0")
                self.emit(f"J {eq_end}")
                self.emit(f"{eq_true}:")
                self.emit("ADDI $v0, $zero, 1")
                self.emit(f"{eq_end}:")
            elif node.op == "/=":
                neq_true = self._make_label("neq_true")
                neq_end = self._make_label("neq_end")
                self.emit(f"BNE $t0, $v0, {neq_true}")
                self.emit("ADDI $v0, $zero, 0")
                self.emit(f"J {neq_end}")
                self.emit(f"{neq_true}:")
                self.emit("ADDI $v0, $zero, 1")
                self.emit(f"{neq_end}:")

    def _emit_print_decimal(self) -> None:
        self.emit("ADD $a0, $v0, $zero")
        self.emit("OUTNUM $a0")

    def _compile_print(self, node: Print) -> None:
        if isinstance(node.value, StrLit):
            addr = self._alloc_string(node.value.value)
            self.emit(f"ADDI $a0, $zero, {addr}")
            self.emit("PRINTS $a0")
        elif isinstance(node.value, VarLit):
            if node.value.name not in self.globals:
                msg = f"Undefined variable: {node.value.name}"
                raise ValueError(msg)
            if node.value.name in self.string_vars:
                self.emit(f"LW $a0, {self.globals[node.value.name]}($gp)")
                self.emit("PRINTS $a0")
            else:
                self.compile_expr(node.value)
                self._emit_print_decimal()
        else:
            self.compile_expr(node.value)
            self._emit_print_decimal()

    def _compile_read(self) -> None:
        label_done = self._make_label("read_done")
        tmp_len = self._alloc_var("__read_len")
        tmp_ptr = self._alloc_var("__read_ptr")
        tmp_buf = self.read_buffer_base
        self.read_buffer_base += 256
        read_empty = self._make_label("read_empty")
        self.emit(f"LW $t0, {IN_CTRL}($zero)")
        self.emit(f"BEQ $t0, $zero, {read_empty}")
        self.emit("ADDI $v0, $zero, 0")
        self.emit(f"SW $v0, {tmp_len}($gp)")
        self.emit(f"ADDI $t1, $zero, {tmp_buf + 4}")
        self.emit(f"SW $t1, {tmp_ptr}($gp)")
        read_loop = self._make_label("read_char")
        read_end = self._make_label("read_end")
        self.emit(f"{read_loop}:")
        self.emit(f"LW $t0, {IN_CTRL}($zero)")
        self.emit(f"BEQ $t0, $zero, {read_end}")
        self.emit(f"LW $t0, {IN_ADDR}($zero)")
        self.emit("ADDI $t1, $t0, -10")
        self.emit(f"BEQ $t1, $zero, {read_end}")
        self.emit(f"LW $t1, {tmp_ptr}($gp)")
        self.emit("SW $t0, 0($t1)")
        self.emit(f"LW $t1, {tmp_ptr}($gp)")
        self.emit("ADDI $t1, $t1, 4")
        self.emit(f"SW $t1, {tmp_ptr}($gp)")
        self.emit(f"LW $t0, {tmp_len}($gp)")
        self.emit("ADDI $t0, $t0, 1")
        self.emit(f"SW $t0, {tmp_len}($gp)")
        self.emit(f"J {read_loop}")
        self.emit(f"{read_end}:")
        self.emit(f"LW $t0, {tmp_len}($gp)")
        self.emit(f"SW $t0, {tmp_buf}($gp)")
        self.emit(f"ADDI $v0, $zero, {tmp_buf}")
        self.emit(f"J {label_done}")
        self.emit(f"{read_empty}:")
        self.emit("ADDI $v0, $zero, 0")
        self.emit(f"SW $v0, {tmp_buf}($gp)")
        self.emit(f"ADDI $v0, $zero, {tmp_buf}")
        self.emit(f"{label_done}:")

    def _compile_call(self, node: FuncCall) -> None:
        if node.name not in self.functions:
            msg = f"Unknown function: {node.name}"
            raise ValueError(msg)
        frame = 4 * (len(node.args) + 1)
        self.emit(f"ADDI $sp, $sp, -{frame}")
        self.emit("SW $ra, 0($sp)")
        for i, arg in enumerate(node.args):
            self.compile_expr(arg)
            self.emit(f"SW $v0, {4 * (i + 1)}($sp)")
        self.emit(f"JAL {self.functions[node.name]}")
        self.emit("LW $ra, 0($sp)")
        self.emit(f"ADDI $sp, $sp, {frame}")

    def _compile_loop(self, node: LoopExpr) -> None:
        var_off = self._alloc_var(node.var)
        label_loop = self._make_label("loop")
        label_end = self._make_label("loop_end")
        self.compile_expr(node.start)
        self.emit(f"SW $v0, {var_off}($gp)")
        self.emit(f"{label_loop}:")
        self.compile_expr(node.end)
        self.emit("ADD $t1, $v0, $zero")
        self.emit(f"LW $t0, {var_off}($gp)")
        self.emit("SLT $v0, $t1, $t0")
        self.emit(f"BNE $v0, $zero, {label_end}")
        self.compile_expr(node.body)
        self.emit(f"LW $t0, {var_off}($gp)")
        self.emit("ADDI $t0, $t0, 1")
        self.emit(f"SW $t0, {var_off}($gp)")
        self.emit(f"J {label_loop}")
        self.emit(f"{label_end}:")