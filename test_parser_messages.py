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
            "const; pi: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ ';'"],
            "semicolon_right_after_const_single_lex_error",
        ),
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
            "con@#st pi: real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимые символы: «@», «#»)",
            ],
            "multiple_invalid_symbols_in_const_prefix",
        ),
        (
            "con@st pi real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимый символ '@')",
                "Пропущено ':' между именем константы и типом данных real",
            ],
            "missing_colon_between_name_and_real_after_broken_const",
        ),
        (
            "const pi real = 3.14;",
            ["Пропущено ':' между именем константы и типом данных real"],
            "missing_colon_before_keyword_real_clear_message",
        ),
        (
            "const pi ral = 3.14;",
            [
                "Пропущено ':' после идентификатора",
                "Ожидался тип данных real (найдено «ral»)",
            ],
            "missing_colon_and_misspelled_real_as_two_errors",
        ),
        (
            "const p@i: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ '@'"],
            "junk_in_name_colon_later_no_false_missing_colon",
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
            "const pi; real = 3.14;",
            [
                "Лексическая ошибка: недопустимый символ ';'",
                "Пропущено ':' после идентификатора",
            ],
            "semicolon_instead_of_colon_two_messages",
        ),
        (
            "const pi@ real = 3.14;",
            [
                "Лексическая ошибка: недопустимый символ '@'",
                "Пропущено ':' после идентификатора",
            ],
            "at_sign_after_name_lex_and_missing_colon",
        ),
        (
            "const! 3pi: real = 3.14;",
            [
                "Лексическая ошибка: недопустимый символ '!'",
                "Ожидался идентификатор имени константы; лексема «3» недопустима — имя не может начинаться с цифры",
            ],
            "bang_then_digit_name_two_errors_no_colon_cascade",
        ),
        (
            "const const pi: real = 3.14;",
            ["Лишнее ключевое слово 'const' перед идентификатором"],
            "duplicate_const_before_identifier",
        ),
        (
            "const !pi: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ '!'"],
            "bang_before_name_after_const",
        ),
        (
            "const! pi: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ '!'"],
            "bang_after_const_keyword",
        ),
        (
            "const #pi: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ '#'"],
            "hash_after_const_simple_invalid_symbol",
        ),
        (
            "const +pi: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ '+'"],
            "plus_after_const_simple_invalid_symbol",
        ),
        (
            "const 3pi resbbal = 3.14;",
            [
                "Ожидался идентификатор имени константы; лексема «3» недопустима — имя не может начинаться с цифры",
                "Ожидался тип данных real (найдено «resbbal»)",
            ],
            "digit_name_then_wrong_real_keyword_continue_parse",
        ),
        (
            "const 3pi: real = 3.14;",
            [
                "Ожидался идентификатор имени константы; лексема «3» недопустима — имя не может начинаться с цифры",
            ],
            "identifier_cannot_start_with_digit_then_valid_rest",
        ),
        (
            "con!st! pi: real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимый символ '!')",
                "Лексическая ошибка: недопустимый символ '!'",
            ],
            "two_bang_typo_const_two_errors",
        ),
        (
            "con@st! 3pi: real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимый символ '@')",
                "Лексическая ошибка: недопустимый символ '!'",
                "Ожидался идентификатор имени константы; лексема «3» недопустима — имя не может начинаться с цифры",
            ],
            "at_inside_const_bang_after_then_digit_three_errors",
        ),
        (
            "co!nst! 3pi: real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимый символ '!')",
                "Лексическая ошибка: недопустимый символ '!'",
                "Ожидался идентификатор имени константы; лексема «3» недопустима — имя не может начинаться с цифры",
            ],
            "co_nst_two_bangs_digit_three_errors",
        ),
        (
            "co!nst! pi: real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимый символ '!')",
                "Лексическая ошибка: недопустимый символ '!'",
            ],
            "co_nst_two_bangs_pi_no_colon_on_second_bang",
        ),
        (
            "con@=;st pi: real = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимые символы: «@», «=», «;»)",
            ],
            "const_typo_lists_all_junk_operators",
        ),
        (
            "@const pi: real = 3.14;",
            ["Лексическая ошибка: недопустимый символ '@'"],
            "leading_at_before_const_keyword",
        ),
        (
            "con@st pi rea@l = 3.14;",
            [
                "Ожидалось ключевое слово const (недопустимый символ '@')",
                "Ожидался тип данных real",
            ],
            "broken_real_rea_at_l_single_type_error",
        ),
        (
            "const pi rea!@l = 3.14;",
            ["Ожидался тип данных real"],
            "broken_real_multiple_junk_single_type_error",
        ),
        (
            'const pi: rea"l = 3.14;',
            ["Ожидался тип данных real"],
            "broken_real_quote_after_colon_single_syntax_error",
        ),
        (
            "const p@i rea#l = 3.14;",
            [
                "Лексическая ошибка: недопустимый символ '@'",
                "Пропущено ':' после идентификатора",
                "Ожидался тип данных real",
            ],
            "broken_real_after_split_name_one_type_error_absorbs_hash",
        ),
    ]

    for src, expected, label in cases:
        got = _messages(src)
        assert got == expected, f"{label}:\nexpected={expected}\ngot={got}\nsource={src!r}"

    print("test_parser_messages: OK (%d cases)" % len(cases))


if __name__ == "__main__":
    main()
