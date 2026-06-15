from __future__ import annotations

from src.emulator.elements import (
    ALU,
    MUX,
    DataMemory,
    InstructionMemory,
    Register,
    Registers,
    StreamIO,
    Summator,
)
from src.isa import Instruction, Opcode, decode


class DataPath:
    def __init__(self, inst_data: list[int], mem_data: dict[int, int], input_bg: list[int]) -> None:
        self.instructions = InstructionMemory(inst_data)
        io = StreamIO(input_bg)
        self.data_mem = DataMemory(mem_data)
        self.data_mem.set_io(io)
        self.alu = ALU()
        self.registers = Registers()
        self.pc_reg = Register()
        self.ir_reg = Register()
        self.pc_mux = MUX()
        self.pc_summator = Summator()
        self.current_inst: Instruction | None = None
        self.halted = False
        self.branch_taken = False
        self.prints_state: dict[str, int] = {}
        self.outnum_state: dict[str, int | list[int]] = {}

    def outnum_step(self) -> bool:
        assert self.current_inst is not None
        st = self.outnum_state
        pc = self.pc_reg.val
        if st.get("inst_pc") != pc:
            st = {"inst_pc": pc}
            self.outnum_state = st
        if "digits" not in st:
            val = self.registers.get(self.current_inst.rs)
            if val == 0:
                self.data_mem.write_word(0x00007F00, ord("0"))
                self.outnum_state = {}
                return True
            digits: list[int] = []
            n = val
            while n > 0:
                digits.append(ord("0") + (n % 10))
                n //= 10
            st["digits"] = list(reversed(digits))
            st["pos"] = 0
        digits_list = st["digits"]
        assert isinstance(digits_list, list)
        pos = int(st["pos"])
        if pos >= len(digits_list):
            self.data_mem.write_word(0x00007F00, 10)
            self.outnum_state = {}
            return True
        self.data_mem.write_word(0x00007F00, digits_list[pos])
        st["pos"] = pos + 1
        return False

    @property
    def io(self) -> StreamIO:
        return self.data_mem.io

    def latch_pc(self) -> None:
        pc_val = self.pc_reg.latch_reg_()
        self.pc_summator.set_val(pc_val)
        self.instructions.set(pc_val)

    def fetch_instruction(self) -> None:
        self.ir_reg.set(self.instructions.fetch_instruction_())

    def latch_ir(self) -> Instruction:
        word = self.ir_reg.latch_reg_()
        self.current_inst = decode(word)
        if self.current_inst.opcode == Opcode.HALT:
            self.halted = True
        return self.current_inst

    def latch_pc_summator(self) -> None:
        self.pc_mux.in_(2, self.pc_summator.latch_sum_())

    def latch_pc_mux(self, num: int) -> None:
        self.pc_reg.set(self.pc_mux.sel_(num))

    def do_branch(self) -> None:
        assert self.current_inst is not None
        self.pc_reg.set(self.current_inst.addr)
        self.branch_taken = True

    def do_branch_reg(self) -> None:
        assert self.current_inst is not None
        self.pc_reg.set(self.registers.get(self.current_inst.rs))
        self.branch_taken = True

    def do_branch_cond(self, when_eq: bool) -> None:
        assert self.current_inst is not None
        eq = self.registers.get(self.current_inst.rs) == self.registers.get(self.current_inst.rt)
        if (when_eq and eq) or (not when_eq and not eq):
            new_pc = self.pc_reg.val + 1 + self.current_inst.imm
            self.pc_reg.set(new_pc)
            self.branch_taken = True

    def do_jal(self) -> None:
        assert self.current_inst is not None
        self.registers.set(31, self.pc_reg.val + 1)
        self.pc_reg.set(self.current_inst.addr)
        self.branch_taken = True

    def prints_step(self) -> bool:
        assert self.current_inst is not None
        pc = self.pc_reg.val
        st = self.prints_state
        if st.get("inst_pc") != pc:
            st = {
                "inst_pc": pc,
                "addr": self.registers.get(self.current_inst.rs),
                "len": self.data_mem.read_word(
                    self.registers.get(self.current_inst.rs)
                ),
                "pos": 0,
            }
            self.prints_state = st
        if st["pos"] >= st["len"]:
            self.prints_state = {}
            return True
        ch_addr = st["addr"] + 4 * (st["pos"] + 1)
        ch = self.data_mem.read_word(ch_addr)
        self.data_mem.write_word(0x00007F00, ch)
        st["pos"] += 1
        return st["pos"] >= st["len"]
