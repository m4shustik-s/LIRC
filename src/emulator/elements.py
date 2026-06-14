from __future__ import annotations

import operator
from enum import Enum

from src.config import IOMemoryMapping


class ALU_OP(Enum):
    ADD = operator.add
    SUB = operator.sub
    MUL = operator.mul
    DIV = operator.floordiv
    SLT = "SLT"
    EQ = "EQ"
    PASS = "PASS"


class MUX:
    def __init__(self) -> None:
        self.val: dict[int, int] = {}

    def in_(self, name: int, val: int) -> None:
        self.val[name] = val

    def sel_(self, name: int) -> int:
        return self.val.get(name, 0)


class DEMUX:
    def __init__(self) -> None:
        self.val: int = 0

    def in_(self, val: int) -> None:
        self.val = val

    def sel_(self) -> int:
        return self.val


class Summator:
    def __init__(self) -> None:
        self.val: int = 0

    def set_val(self, val: int) -> None:
        self.val = val

    def latch_sum_(self) -> int:
        return self.val + 1


class Registers:
    def __init__(self, size: int = 32) -> None:
        self.registers: list[int] = [0] * size

    def get(self, num: int) -> int:
        return self.registers[num]

    def set(self, num: int, val: int) -> None:
        self.registers[num] = val & 0xFFFFFFFF

    def latch_left_reg_(self, num: int) -> int:
        return self.get(num)

    def latch_right_reg_(self, num: int) -> int:
        return self.get(num)


class Register:
    def __init__(self) -> None:
        self.val: int = 0

    def set(self, val: int) -> None:
        self.val = val

    def latch_reg_(self) -> int:
        return self.val


class InstructionMemory:
    def __init__(self, inst: list[int]) -> None:
        self.instructions = inst
        self.ind: int = 0

    def set(self, val: int) -> None:
        self.ind = val

    def fetch_instruction_(self) -> int:
        if self.ind >= len(self.instructions):
            return 0xFC000000
        return self.instructions[self.ind]


class StreamIO:
    def __init__(self, input_data: list[int]) -> None:
        self.input_buffer = list(input_data)
        self.input_pos = 0
        self.output_buffer: list[int] = []

    def in_ready(self) -> int:
        return 1 if self.input_pos < len(self.input_buffer) else 0

    def read_char(self) -> int:
        if self.input_pos >= len(self.input_buffer):
            return 0
        ch = self.input_buffer[self.input_pos]
        self.input_pos += 1
        return ch

    def write_char(self, val: int) -> None:
        self.output_buffer.append(val & 0xFF)


class DataMemory:
    def __init__(self, init_data: dict[int, int]) -> None:
        self.mem: dict[int, int] = dict(init_data)
        self.io = StreamIO([])

    def set_io(self, io: StreamIO) -> None:
        self.io = io

    def read_word(self, addr: int) -> int:
        if addr == IOMemoryMapping.IN_CTRL.value:
            return self.io.in_ready()
        if addr == IOMemoryMapping.IN.value:
            return self.io.read_char()
        return self.mem.get(addr, 0)

    def write_word(self, addr: int, val: int) -> None:
        if addr == IOMemoryMapping.OUT.value:
            self.io.write_char(val)
        else:
            self.mem[addr] = val & 0xFFFFFFFF


class ALU:
    def __init__(self) -> None:
        self.left_input: int = 0
        self.right_input: int = 0

    def set_left(self, val: int) -> None:
        self.left_input = val

    def set_right(self, val: int) -> None:
        self.right_input = val

    def alu_op_(self, op_type: ALU_OP | int) -> int:
        if op_type == ALU_OP.PASS or op_type == -1:
            return self.right_input & 0xFFFFFFFF
        if op_type == ALU_OP.SLT:
            return 1 if self.left_input < self.right_input else 0
        if op_type == ALU_OP.EQ:
            return 1 if self.left_input == self.right_input else 0
        if isinstance(op_type, ALU_OP):
            if op_type == ALU_OP.DIV and self.right_input == 0:
                return 0
            result = op_type.value(self.left_input, self.right_input)
            return int(result) & 0xFFFFFFFF
        return 0


class LoadStoreUnit:
    def __init__(self, data_memory: DataMemory) -> None:
        self.data = data_memory
        self.address: int = 0
        self.reg_value: int = 0

    def set_reg(self, reg: int) -> None:
        self.reg_value = reg

    def set_address(self, address: int) -> None:
        self.address = address

    def store_(self) -> None:
        self.data.write_word(self.address, self.reg_value)

    def load_(self) -> int:
        return self.data.read_word(self.address)
