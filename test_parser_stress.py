"""Стресс-тест парсера на массово испорченных строках.

Цель:
- проверить, что анализ не падает на "грязном" вводе;
- убедиться, что на испорченных строках фиксируются ошибки.

Запуск:
    python test_parser_stress.py
"""

from __future__ import annotations

import os
import random
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
TEXT_EDITOR_DIR = os.path.join(ROOT, "text_editor")
if TEXT_EDITOR_DIR not in sys.path:
    sys.path.insert(0, TEXT_EDITOR_DIR)

from scanner import Scanner  # noqa: E402
from parser import Parser  # noqa: E402


BASE = "const PI: real = 3.14;"
BAD_CHARS = "@#!?,$%^&*()[]{}\\|`~\"'"


def _mutate_once(text: str, rnd: random.Random) -> str:
    s = list(text)
    action = rnd.choice(["replace_bad", "insert_bad", "delete", "repeat_bad"])
    pos = rnd.randrange(0, len(s))
    if action == "replace_bad":
        s[pos] = rnd.choice(BAD_CHARS)
    elif action == "insert_bad":
        s.insert(pos, rnd.choice(BAD_CHARS))
    elif action == "delete" and len(s) > 1:
        s.pop(pos)
    elif action == "repeat_bad":
        bad = rnd.choice(BAD_CHARS)
        s.insert(pos, bad * rnd.randint(2, 5))
    return "".join(s)


def _analyze(src: str) -> tuple[int, int]:
    tokens, lex = Scanner().analyze(src)
    _, syn = Parser().analyze(tokens)
    return len(lex), len(syn)


def main():
    rnd = random.Random(42)
    samples = []

    # Явно плохие шаблоны.
    samples.extend(
        [
            "cons@t PI: real = 3.14;",
            "con;st PI: real = 3.14;",
            "co###nst PI: real = 3.14;",
            "const PI real = .14;",
            "const : real = 3.14;",
            "??? garbage",
            "const PI: real = 3.k4;",
        ]
    )

    # Генерируем дополнительные мутации.
    for _ in range(120):
        t = BASE
        for _ in range(rnd.randint(1, 4)):
            t = _mutate_once(t, rnd)
        samples.append(t)

    # На исходной строке ошибок быть не должно.
    lex_ok, syn_ok = _analyze(BASE)
    assert lex_ok == 0 and syn_ok == 0, "base string must be valid"

    # На большинстве испорченных строк должна быть хотя бы одна ошибка
    # (лексическая или синтаксическая), и разбор не должен падать.
    bad_count = 0
    for i, src in enumerate(samples):
        lex, syn = _analyze(src)
        if (lex + syn) > 0:
            bad_count += 1

    ratio = bad_count / len(samples)
    assert ratio >= 0.95, f"too many mutated samples parsed as valid: ratio={ratio:.3f}"

    print("test_parser_stress: OK (%d mutated samples)" % len(samples))


if __name__ == "__main__":
    main()
