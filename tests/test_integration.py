from __future__ import annotations

import pytest

from tests.run_chain import load_golden, run_program


def test_hello() -> None:
    golden = load_golden("hello")
    result = run_program("hello")
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert result["output"] == golden["expected_output"]


def test_expr_demo() -> None:
    golden = load_golden("expr_demo")
    result = run_program("expr_demo")
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert result["output"] == golden["expected_output"]


def test_cat() -> None:
    golden = load_golden("cat")
    result = run_program("cat", golden.get("input", "hello"))
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert golden["expected_output"] in result["output"]


def test_hello_user_name() -> None:
    golden = load_golden("hello_user_name")
    result = run_program("hello_user_name", golden["input"])
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert result["output"] == golden["expected_output"]


def test_sort() -> None:
    golden = load_golden("sort")
    result = run_program("sort")
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert result["output"] == golden["expected_output"]


@pytest.mark.slow
def test_prob1() -> None:
    result = run_program("prob1", log_limit=100, max_ticks=100_000_000)
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert "906609" in result["output"]


def test_int64() -> None:
    result = run_program("int64")
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert "0" in result["output"]


def test_harvard_check() -> None:
    result = run_program("harvard_check")
    print(f"Лог симуляции:\n{result["log_excerpt"]}\n")
    print(f"Вывод:\n{result["output"]}\n")
    print(f"Ассемблер:\n{result["asm"]}\n")
    assert "0" in result["output"]
    assert "256" in result["output"]


def test_imports() -> None:
    import src.emulator.cu  # noqa: F401
    import src.emulator.microcode  # noqa: F401
    import src.translator.translator  # noqa: F401


def test_parser_ast() -> None:
    from io import StringIO

    from src.translator.ast_parser import NumLit, Parser
    from src.translator.tokenizer import Tokenizer

    parser = Parser(Tokenizer(StringIO("(setq x 5)")))
    nodes = parser.parse()
    assert len(nodes) == 1
    assert nodes[0].name == "x"
    assert isinstance(nodes[0].value, NumLit)


def test_microcode_rom() -> None:
    from src.emulator.microcode import mc_dispatch, mc_rom

    assert "ADD" in mc_dispatch
    assert len(mc_rom) > 20
