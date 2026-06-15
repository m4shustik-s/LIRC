from __future__ import annotations

from dataclasses import dataclass

from src.emulator.datapath import DataPath
from src.emulator.elements import ALU_OP


@dataclass
class Microcode:
    name: str = ""
    latch_pc: bool = False
    fetch_instruction: bool = False
    latch_ir: bool = False
    exec_r_type: ALU_OP | None = None
    exec_addi: bool = False
    exec_lw: bool = False
    exec_sw: bool = False
    exec_beq: bool = False
    exec_bne: bool = False
    exec_j: bool = False
    exec_jal: bool = False
    exec_jr: bool = False
    exec_prints: bool = False
    exec_outnum: bool = False
    pc_epilogue: bool = False
    branching: int | None = None

    def execute(self, datapath: DataPath, dispatch: dict[str, int], end_idx: int) -> int | None:
        if self.branching is not None:
            return self.branching

        inst = datapath.current_inst

        if self.latch_pc:
            datapath.latch_pc()
        if self.fetch_instruction:
            datapath.fetch_instruction()
        if self.latch_ir:
            decoded = datapath.latch_ir()
            if datapath.halted:
                return end_idx
            return dispatch.get(decoded.opcode.value, end_idx)

        if inst and self.exec_r_type is not None:
            rs = datapath.registers.get(inst.rs)
            rt = datapath.registers.get(inst.rt)
            datapath.alu.set_left(rs)
            datapath.alu.set_right(rt)
            result = datapath.alu.alu_op_(self.exec_r_type)
            datapath.registers.set(inst.rd, result)

        if inst and self.exec_addi:
            rs = datapath.registers.get(inst.rs)
            datapath.registers.set(inst.rt, (rs + inst.imm) & 0xFFFFFFFF)

        if inst and self.exec_lw:
            addr = (datapath.registers.get(inst.rs) + inst.imm) & 0xFFFFFFFF
            val = datapath.data_mem.read_word(addr)
            datapath.registers.set(inst.rt, val)

        if inst and self.exec_sw:
            addr = (datapath.registers.get(inst.rs) + inst.imm) & 0xFFFFFFFF
            datapath.data_mem.write_word(addr, datapath.registers.get(inst.rt))

        if inst and self.exec_beq:
            datapath.do_branch_cond(True)
        if inst and self.exec_bne:
            datapath.do_branch_cond(False)
        if inst and self.exec_j:
            datapath.do_branch()
        if inst and self.exec_jal:
            datapath.do_jal()
        if inst and self.exec_jr:
            datapath.do_branch_reg()
        if inst and self.exec_prints:
            if not datapath.prints_step():
                return dispatch["PRINTS"]
        if inst and self.exec_outnum:
            if not datapath.outnum_step():
                return dispatch["OUTNUM"]

        if self.pc_epilogue:
            if not datapath.branch_taken:
                datapath.latch_pc_summator()
                datapath.latch_pc_mux(2)
            datapath.branch_taken = False
            return 0

        return None


def _seq(name: str, steps: list[Microcode]) -> tuple[str, list[Microcode]]:
    steps = steps + [Microcode(f"{name}_to_epilogue", branching=-1)]
    return name, steps


def build_microcode_rom() -> tuple[tuple[Microcode, ...], dict[str, int]]:
    parts: list[tuple[str, list[Microcode]]] = [
        (
            "start",
            [
                Microcode("fetch_pc", latch_pc=True),
                Microcode("fetch_inst", fetch_instruction=True),
                Microcode("decode", latch_ir=True),
            ],
        ),
        _seq("ADD", [Microcode("add", exec_r_type=ALU_OP.ADD)]),
        _seq("SUB", [Microcode("sub", exec_r_type=ALU_OP.SUB)]),
        _seq("MUL", [Microcode("mul", exec_r_type=ALU_OP.MUL)]),
        _seq("DIV", [Microcode("div", exec_r_type=ALU_OP.DIV)]),
        _seq("SLT", [Microcode("slt", exec_r_type=ALU_OP.SLT)]),
        _seq("ADDI", [Microcode("addi", exec_addi=True)]),
        _seq("LW", [Microcode("lw", exec_lw=True)]),
        _seq("SW", [Microcode("sw", exec_sw=True)]),
        _seq("BEQ", [Microcode("beq", exec_beq=True)]),
        _seq("BNE", [Microcode("bne", exec_bne=True)]),
        _seq("J", [Microcode("j", exec_j=True)]),
        _seq("JAL", [Microcode("jal", exec_jal=True)]),
        _seq("JR", [Microcode("jr", exec_jr=True)]),
        _seq("PRINTS", [Microcode("prints", exec_prints=True)]),
        _seq("OUTNUM", [Microcode("outnum", exec_outnum=True)]),
        ("HALT", [Microcode("halt", branching=-1)]),
        ("end", [Microcode("pc_epilogue", pc_epilogue=True)]),
    ]

    flat: list[Microcode] = []
    dispatch: dict[str, int] = {}
    idx = 0
    for name, seq in parts:
        dispatch[name] = idx
        flat.extend(seq)
        idx += len(seq)

    end_idx = dispatch["end"]
    for mc in flat:
        if mc.branching == -1:
            mc.branching = end_idx

    return tuple(flat), dispatch


mc_rom, mc_dispatch = build_microcode_rom()
MC_END_IDX = mc_dispatch["end"]
