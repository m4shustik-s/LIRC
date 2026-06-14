from __future__ import annotations

import struct
from pathlib import Path

import yaml

from src.assembler.parser import parse_asm, program_to_binary
from src.emulator.cu import format_log_excerpt, run_emulator
from src.translator.main import translate_file

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
GOLDEN = ROOT / "golden"


def run_program(lisp_name: str, input_text: str = "", log_limit: int = 200, max_ticks: int = 10_000_000) -> dict:
    BUILD.mkdir(exist_ok=True)
    lisp_path = ROOT / "examples" / f"{lisp_name}.lisp"
    asm_path = BUILD / f"{lisp_name}.asm"
    prefix = BUILD / lisp_name

    translate_file(lisp_path, asm_path)
    prog = parse_asm(asm_path.read_text(encoding="utf-8"))
    text, data, disasm = program_to_binary(prog)

    text_path = Path(f"{prefix}.text.bin")
    data_path = Path(f"{prefix}.data.bin")
    with text_path.open("wb") as f:
        for w in text:
            f.write(struct.pack("<I", w & 0xFFFFFFFF))
    with data_path.open("wb") as f:
        for w in data:
            f.write(struct.pack("<I", w & 0xFFFFFFFF))

    result = run_emulator(text_path, data_path, input_text, log_limit=log_limit, max_ticks=max_ticks)
    return {
        "output": result.output,
        "ticks": result.ticks,
        "log_excerpt": format_log_excerpt(result, max_lines=30),
        "disasm": "\n".join(disasm),
        "asm": asm_path.read_text(encoding="utf-8"),
        "text_bin_path": text_path,   # <-- НОВОЕ
        "data_bin_path": data_path,   # <-- НОВОЕ
    }


def load_golden(name: str) -> dict:
    path = GOLDEN / f"{name}.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
