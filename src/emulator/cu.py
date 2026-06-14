from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from src.emulator.datapath import DataPath
from src.emulator.microcode import MC_END_IDX, mc_dispatch, mc_rom


@dataclass
class TickLog:
    tick: int
    upc: int
    pc: int
    micro_name: str
    registers: list[int]


@dataclass
class SimulationResult:
    output: str
    ticks: int
    logs: list[TickLog] = field(default_factory=list)
    halted: bool = False


class CU:
    def __init__(self, inst_data: list[int], mem_data: dict[int, int], input_bg: list[int]) -> None:
        self.datapath = DataPath(inst_data, mem_data, input_bg)
        self.mc = mc_rom
        self.dispatch = mc_dispatch
        self.upc = 0
        self.tick = 0
        self.logs: list[TickLog] = []
        self.max_ticks = 10_000_000

    def log_tick(self, micro: object) -> None:
        self.logs.append(
            TickLog(
                tick=self.tick,
                upc=self.upc,
                pc=self.datapath.pc_reg.val,
                micro_name=getattr(micro, "name", ""),
                registers=list(self.datapath.registers.registers),
            )
        )

    def run(self, log_limit: int | None = None) -> SimulationResult:
        while not self.datapath.halted and self.tick < self.max_ticks:
            self.tick += 1
            micro = self.mc[self.upc]
            if log_limit is None or len(self.logs) < log_limit:
                self.log_tick(micro)
            res = micro.execute(self.datapath, self.dispatch, MC_END_IDX)
            if res is not None:
                self.upc = res
            else:
                self.upc += 1
            if self.datapath.halted:
                break
            if self.datapath.pc_reg.val >= len(self.datapath.instructions.instructions):
                break

        out_bytes = self.datapath.io.output_buffer
        output = "".join(chr(b) for b in out_bytes)
        return SimulationResult(output=output, ticks=self.tick, logs=self.logs, halted=self.datapath.halted)


def load_binary(path: Path) -> list[int]:
    data = path.read_bytes()
    return list(struct.unpack(f"<{len(data) // 4}I", data))


def load_data_binary(path: Path) -> dict[int, int]:
    words = load_binary(path)
    return {0x100 + i * 4: w for i, w in enumerate(words)}


def run_emulator(
    text_bin: Path,
    data_bin: Path,
    input_text: str,
    log_limit: int | None = 500,
    max_ticks: int = 10_000_000,
) -> SimulationResult:
    inst = load_binary(text_bin)
    mem = load_data_binary(data_bin)
    input_bg = [ord(c) for c in input_text]
    cu = CU(inst, mem, input_bg)
    cu.max_ticks = max_ticks
    return cu.run(log_limit=log_limit)


def format_log_excerpt(result: SimulationResult, max_lines: int = 40) -> str:
    lines = []
    for entry in result.logs[: max_lines // 2]:
        lines.append(
            f"T{entry.tick:05d} uPC={entry.upc:02d} PC={entry.pc:04d} "
            f"{entry.micro_name} $v0={entry.registers[2]}"
        )
    if len(result.logs) > max_lines:
        lines.append("...")
        for entry in result.logs[-max_lines // 2 :]:
            lines.append(
                f"T{entry.tick:05d} uPC={entry.upc:02d} PC={entry.pc:04d} "
                f"{entry.micro_name} $v0={entry.registers[2]}"
            )
    lines.append(f"TOTAL_TICKS={result.ticks}")
    return "\n".join(lines)
