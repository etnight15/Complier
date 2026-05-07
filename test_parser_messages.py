"""Проверка точных текстов ключевых ошибок парсера.

Запуск:
    python test_parser_messages.py
"""

from __future__ import annotations

import os
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
TEXT_EDITOR_DIR = os.path.join(ROOT, "text_editor")
if TEXT_EDITOR_DIR not in sys.path:
    sys.path.insert(0, TEXT_EDITOR_DIR)

from scanner import Scanner  # noqa: E402
from parser import Parser  # noqa: E402


def _messages(source: str) -> list[str]:
    tokens, _ = Scanner().analyze(source)
    _, syn_errors = Parser().analyze(tokens)
    return [e.message for e in syn_errors]


def main():
    cases = [
        (
            "cons@t pi: real = 3.14;",
            ["Ожидалось ключевое слово const (недопустимый символ '@')"],
            "invalid_symbol_inside_const_single_message",
        ),
        (
            "cons!!!t pi: real = 3.14;",
            ["Ожидалось ключевое слово const (недопустимый символ '!' (повторение: 3 раза))"],
            "invalid_repeated_symbol_inside_const_single_message",
        ),
        (
            "cost pi: real 3.14",
            [
                "Ожидалось ключевое слово const",
                "Лишний идентификатор перед ':'",
                "Отсутствует '='",
                "Отсутствует ';'",
            ],
            "typo_const_and_followup_errors",
        ),
        (
            "const pi: real = 3.k4;",
            ["Ожидалось вещественное число"],
            "bad_float_suffix_single_error",
        ),
        (
            "const const pi: real = 3.14;",
            ["Лишнее ключевое слово 'const' перед идентификатором"],
            "duplicate_const_before_identifier",
        ),
    ]

    for src, expected, label in cases:
        got = _messages(src)
        assert got == expected, f"{label}:\nexpected={expected}\ngot={got}\nsource={src!r}"

    print("test_parser_messages: OK (%d cases)" % len(cases))


if __name__ == "__main__":
    main()
