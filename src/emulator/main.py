from __future__ import annotations

import sys
from pathlib import Path

from src.emulator.cu import format_log_excerpt, load_binary, load_data_binary, run_emulator


def main() -> None:
    if len(sys.argv) < 5:
        print(
            "Usage: python -m src.emulator.main "
            "<text.bin> <data.bin> <input.txt> <output.txt> [log.txt]"
        )
        sys.exit(1)
    text_bin = Path(sys.argv[1])
    data_bin = Path(sys.argv[2])
    input_path = Path(sys.argv[3])
    output_path = Path(sys.argv[4])
    log_path = Path(sys.argv[5]) if len(sys.argv) > 5 else None

    input_text = input_path.read_text(encoding="utf-8") if input_path.exists() else ""
    result = run_emulator(text_bin, data_bin, input_text)

    output_path.write_text(result.output, encoding="utf-8")
    if log_path:
        log_path.write_text(format_log_excerpt(result), encoding="utf-8")


if __name__ == "__main__":
    main()