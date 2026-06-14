from __future__ import annotations

import re
from dataclasses import dataclass

from src.isa import Instruction, Opcode, reg_num


@dataclass
class DataWord:
    address: int
    value: int


@dataclass
class AsmProgram:
    instructions: list[Instruction]
    data: list[DataWord]
    labels_text: dict[str, int]
    labels_data: dict[str, int]


def _parse_imm(token: str) -> int:
    if token.startswith("0x") or token.startswith("0X"):
        return int(token, 16)
    return int(token)


def _parse_mem(text: str) -> tuple[int, int]:
    m = re.match(r"(-?\d+|0x[0-9A-Fa-f]+)\(\$(\w+)\)", text.strip())
    if not m:
        msg = f"Bad memory operand: {text}"
        raise ValueError(msg)
    return reg_num(f"${m.group(2)}"), _parse_imm(m.group(1))


def parse_asm(source: str) -> AsmProgram:
    section = "text"
    text_lines: list[str] = []
    data_entries: list[tuple[str, str]] = []
    labels_text: dict[str, int] = {}
    labels_data: dict[str, int] = {}
    pc = 0
    data_addr = 0x100

    for raw in source.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        if line == ".text":
            section = "text"
            continue
        if line == ".data":
            section = "data"
            continue
        if line.endswith(":"):
            label = line[:-1]
            if section == "text":
                labels_text[label] = pc
            else:
                labels_data[label] = data_addr
            continue
        if section == "text":
            text_lines.append(line)
            pc += 1
        elif ": " in line or (":" in line and ".pascal" in line):
            lbl, rest = line.split(":", 1)
            data_entries.append((lbl.strip(), rest.strip()))
        else:
            data_entries.append(("", line))

    instructions = [_parse_instruction(line, i, labels_text, labels_data) for i, line in enumerate(text_lines)]

    data: list[DataWord] = []
    for label, line in data_entries:
        addr = data_addr
        if label:
            labels_data[label] = addr
        if line.startswith(".pascal"):
            m = re.search(r"\"(.*)\"", line)
            if not m:
                continue
            text = m.group(1)
            data.append(DataWord(addr, len(text)))
            addr += 4
            for ch in text:
                data.append(DataWord(addr, ord(ch)))
                addr += 4
            data_addr = addr
        elif line.startswith(".word"):
            data.append(DataWord(addr, _parse_imm(line.split()[1])))
            data_addr = addr + 4

    return AsmProgram(instructions, data, labels_text, labels_data)


def _label_val(token: str, labels_text: dict[str, int], labels_data: dict[str, int]) -> int:
    if token in labels_text:
        return labels_text[token]
    if token in labels_data:
        return labels_data[token]
    return _parse_imm(token)


def _parse_instruction(
    line: str,
    pc: int,
    labels_text: dict[str, int],
    labels_data: dict[str, int],
) -> Instruction:
    parts = [p for p in line.replace(",", " ").split() if p]
    op = parts[0].upper()

    if op == "HALT":
        return Instruction(Opcode.HALT)
    if op == "J":
        return Instruction(Opcode.J, addr=_label_val(parts[1], labels_text, labels_data))
    if op == "JAL":
        return Instruction(Opcode.JAL, addr=_label_val(parts[1], labels_text, labels_data))
    if op == "PRINTS":
        return Instruction(Opcode.PRINTS, rs=reg_num(parts[1]))
    if op == "OUTNUM":
        return Instruction(Opcode.OUTNUM, rs=reg_num(parts[1]))
    if op == "JR":
        return Instruction(Opcode.JR, rs=reg_num(parts[1]))
    if op in ("ADD", "SUB", "MUL", "DIV", "SLT"):
        return Instruction(Opcode[op], rd=reg_num(parts[1]), rs=reg_num(parts[2]), rt=reg_num(parts[3]))
    if op == "ADDI":
        rt = reg_num(parts[1])
        rs = reg_num(parts[2])
        imm_tok = parts[3]
        imm = labels_data[imm_tok] if imm_tok in labels_data else _parse_imm(imm_tok)
        return Instruction(Opcode.ADDI, rs=rs, rt=rt, imm=imm)
    if op in ("LW", "SW"):
        rt = reg_num(parts[1])
        rs, imm = _parse_mem(parts[2])
        opc = Opcode.LW if op == "LW" else Opcode.SW
        return Instruction(opc, rs=rs, rt=rt, imm=imm)
    if op in ("BEQ", "BNE"):
        rs = reg_num(parts[1])
        rt = reg_num(parts[2])
        target = _label_val(parts[3], labels_text, labels_data)
        imm = target - (pc + 1)
        opc = Opcode.BEQ if op == "BEQ" else Opcode.BNE
        return Instruction(opc, rs=rs, rt=rt, imm=imm)
    msg = f"Unknown instruction: {line}"
    raise ValueError(msg)


def program_to_binary(prog: AsmProgram) -> tuple[list[int], list[int], list[str]]:
    from src.isa import decode, disasm, encode

    text = [encode(i) for i in prog.instructions]
    data_map = {d.address: d.value for d in prog.data}
    max_addr = max(data_map) if data_map else 0x100
    data = [data_map.get(addr, 0) for addr in range(0x100, max_addr + 4, 4)]
    disasm_lines = [disasm(decode(word), pc * 4) for pc, word in enumerate(text)]
    return text, data, disasm_lines
