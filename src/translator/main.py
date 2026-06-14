from __future__ import annotations

import sys
from pathlib import Path

from src.translator.ast_parser import Parser
from src.translator.tokenizer import Tokenizer
from src.translator.translator import Translator


def _strip_line_comments(source: str) -> str:
    lines = []
    for line in source.splitlines():
        if ";" in line:
            line = line.split(";", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def translate_file(source_path: Path, output_path: Path) -> str:
    source = _strip_line_comments(source_path.read_text(encoding="utf-8"))
    from io import StringIO

    parser = Parser(Tokenizer(StringIO(source)))
    parser.pre_scan_functions(source)
    ast_nodes = parser.parse()
    asm = Translator().translate(ast_nodes)
    output_path.write_text(asm, encoding="utf-8")
    return asm


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m src.translator.main <input.lisp> <output.asm>")
        sys.exit(1)
    translate_file(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
