from __future__ import annotations

import struct
import sys
from pathlib import Path

from src.assembler.parser import parse_asm, program_to_binary


def write_binary(words: list[int], path: Path) -> None:
    with path.open("wb") as f:
        for w in words:
            f.write(struct.pack("<I", w & 0xFFFFFFFF))


def assemble_file(asm_path: Path, prefix: Path) -> tuple[Path, Path, Path]:
    source = asm_path.read_text(encoding="utf-8")
    prog = parse_asm(source)
    text, data, disasm_lines = program_to_binary(prog)
    text_path = Path(f"{prefix}.text.bin")
    data_path = Path(f"{prefix}.data.bin")
    disasm_path = Path(f"{prefix}.disasm.txt")
    write_binary(text, text_path)
    write_binary(data, data_path)
    disasm_path.write_text("\n".join(disasm_lines) + "\n", encoding="utf-8")
    return text_path, data_path, disasm_path


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m src.assembler.main <input.asm> <output_prefix>")
        sys.exit(1)
    assemble_file(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
