from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config import REG_NAMES


class Opcode(str, Enum):
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    SLT = "SLT"
    ADDI = "ADDI"
    LW = "LW"
    SW = "SW"
    BEQ = "BEQ"
    BNE = "BNE"
    J = "J"
    JAL = "JAL"
    PRINTS = "PRINTS"
    OUTNUM = "OUTNUM"
    JR = "JR"
    HALT = "HALT"
    NOP = "NOP"


@dataclass
class Instruction:
    opcode: Opcode
    rs: int = 0
    rt: int = 0
    rd: int = 0
    imm: int = 0
    addr: int = 0
    raw: int = 0

    def to_dict(self) -> dict:
        return {
            "opcode": self.opcode.value,
            "rs": self.rs,
            "rt": self.rt,
            "rd": self.rd,
            "imm": self.imm,
            "addr": self.addr,
        }


OPCODE_TOP: dict[Opcode, int] = {
    Opcode.ADD: 0x00,
    Opcode.SUB: 0x00,
    Opcode.MUL: 0x1C,
    Opcode.DIV: 0x00,
    Opcode.SLT: 0x00,
    Opcode.JR: 0x00,
    Opcode.ADDI: 0x08,
    Opcode.LW: 0x23,
    Opcode.SW: 0x2B,
    Opcode.BEQ: 0x04,
    Opcode.BNE: 0x05,
    Opcode.PRINTS: 0x30,
    Opcode.OUTNUM: 0x31,
    Opcode.J: 0x02,
    Opcode.JAL: 0x03,
    Opcode.HALT: 0x3F,
}

FUNCT: dict[Opcode, int] = {
    Opcode.ADD: 0x20,
    Opcode.SUB: 0x22,
    Opcode.MUL: 0x02,
    Opcode.DIV: 0x1A,
    Opcode.SLT: 0x2A,
    Opcode.JR: 0x08,
}


def reg_num(name: str) -> int:
    if name.startswith("$"):
        if name in REG_NAMES:
            return REG_NAMES[name]
        if name[1:].isdigit():
            return int(name[1:])
    if name.isdigit():
        return int(name)
    msg = f"Unknown register: {name}"
    raise ValueError(msg)


def encode(inst: Instruction) -> int:
    op = inst.opcode
    if op == Opcode.HALT:
        return OPCODE_TOP[Opcode.HALT] << 26
    if op in (Opcode.J, Opcode.JAL):
        return (OPCODE_TOP[op] << 26) | (inst.addr & 0x3FFFFFF)
    if op in (Opcode.ADDI, Opcode.LW, Opcode.SW, Opcode.BEQ, Opcode.BNE, Opcode.PRINTS, Opcode.OUTNUM):
        imm = inst.imm & 0xFFFF
        if inst.imm < 0:
            imm = inst.imm & 0xFFFF
        return (OPCODE_TOP[op] << 26) | (inst.rs << 21) | (inst.rt << 16) | imm
    if op in FUNCT:
        return (
            (OPCODE_TOP[op] << 26)
            | (inst.rs << 21)
            | (inst.rt << 16)
            | (inst.rd << 11)
            | FUNCT[op]
        )
    msg = f"Cannot encode {op}"
    raise ValueError(msg)


def decode(word: int) -> Instruction:
    top = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    funct = word & 0x3F
    imm_raw = word & 0xFFFF
    imm = imm_raw if imm_raw < 0x8000 else imm_raw - 0x10000
    addr = word & 0x3FFFFFF

    if top == 0x3F:
        return Instruction(Opcode.HALT, raw=word)
    if top == 0x02:
        return Instruction(Opcode.J, addr=addr, raw=word)
    if top == 0x03:
        return Instruction(Opcode.JAL, addr=addr, raw=word)
    if top == 0x08:
        return Instruction(Opcode.ADDI, rs=rs, rt=rt, imm=imm, raw=word)
    if top == 0x23:
        return Instruction(Opcode.LW, rs=rs, rt=rt, imm=imm, raw=word)
    if top == 0x2B:
        return Instruction(Opcode.SW, rs=rs, rt=rt, imm=imm, raw=word)
    if top == 0x04:
        return Instruction(Opcode.BEQ, rs=rs, rt=rt, imm=imm, raw=word)
    if top == 0x05:
        return Instruction(Opcode.BNE, rs=rs, rt=rt, imm=imm, raw=word)
    if top == 0x30:
        return Instruction(Opcode.PRINTS, rs=rs, raw=word)
    if top == 0x31:
        return Instruction(Opcode.OUTNUM, rs=rs, raw=word)
    if top == 0x1C and funct == 0x02:
        return Instruction(Opcode.MUL, rs=rs, rt=rt, rd=rd, raw=word)
    if top == 0x00:
        for op, f in FUNCT.items():
            if f == funct:
                return Instruction(op, rs=rs, rt=rt, rd=rd, raw=word)
    return Instruction(Opcode.NOP, raw=word)


def disasm(inst: Instruction, pc: int = 0) -> str:
    if inst.opcode == Opcode.HALT:
        return f"{pc:08X} - {inst.raw:08X} - halt"
    if inst.opcode in (Opcode.J, Opcode.JAL):
        return f"{pc:08X} - {inst.raw:08X} - {inst.opcode.value.lower()} {inst.addr}"
    if inst.opcode in (Opcode.ADDI, Opcode.LW, Opcode.SW, Opcode.BEQ, Opcode.BNE):
        return (
            f"{pc:08X} - {inst.raw:08X} - {inst.opcode.value.lower()} "
            f"${inst.rt}, {inst.imm}(${inst.rs})"
        )
    if inst.opcode == Opcode.PRINTS:
        return f"{pc:08X} - {inst.raw:08X} - prints ${inst.rs}"
    if inst.opcode == Opcode.OUTNUM:
        return f"{pc:08X} - {inst.raw:08X} - outnum ${inst.rs}"
    if inst.opcode == Opcode.JR:
        return f"{pc:08X} - {inst.raw:08X} - jr ${inst.rs}"
    return (
        f"{pc:08X} - {inst.raw:08X} - {inst.opcode.value.lower()} "
        f"${inst.rd}, ${inst.rs}, ${inst.rt}"
    )
