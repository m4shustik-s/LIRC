from __future__ import annotations

from pathlib import Path

import yaml

from tests.run_chain import GOLDEN, ROOT, run_program


def expand_golden(name: str) -> None:
    old_path = GOLDEN / f"{name}.yaml"
    old = yaml.safe_load(old_path.read_text(encoding="utf-8"))

    lisp_path = ROOT / "examples" / f"{name}.lisp"
    stdin_text = old.get("input", "")

    result = run_program(name, stdin_text)

    new_golden = {
        "in_source": lisp_path.read_text(encoding="utf-8"),
        "in_stdin": stdin_text,
        "out_code_asm": result["asm"],
        "out_code_hex": result["disasm"],
        "out_code_text_bin": result["text_bin_path"].read_bytes(),  # <-- bytes
        "out_code_data_bin": result["data_bin_path"].read_bytes(),  # <-- bytes
        "out_stdout": result["output"],
        "out_log": result["log_excerpt"],
        "expected_output": old["expected_output"],
        "input": stdin_text,
    }

    old_path.write_text(
        yaml.dump(new_golden, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    for test_name in ["hello", "cat", "expr_demo", "harvard_check",
                       "hello_user_name", "int64", "prob1", "sort"]:
        print(f"Processing {test_name}...")
        expand_golden(test_name)