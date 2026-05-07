"""Матрица проверок лексера/парсера под грамматику:
const <identifier>: real = <float>;

Запуск:
    python test_parser_matrix.py
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


def _analyze(source: str) -> tuple[int, int]:
    tokens, lex_errors = Scanner().analyze(source)
    _, syn_errors = Parser().analyze(tokens)
    return len(lex_errors), len(syn_errors)


def main():
    cases = [
        ("const PI: real = 3.14;", 0, 0, "golden"),
        ("const NEG: real = -3.14;", 0, 0, "negative_float_ok"),
        ("const A: real = 1.0; const B: real = 2.0;", 0, 1, "two_decls_trailing_tokens"),
        ("", 0, 1, "empty_line"),
        (";;;;", 0, 7, "only_semicolons_no_const"),
        ("cont X: real = 1.0;", 0, 2, "const_typo"),
        ("con=st X: real = 1.0;", 0, 4, "const_typo_with_equal"),
        ("con;st X: real = 1.0;", 0, 6, "const_typo_with_semicolon"),
        ("co@nst X: real = 1.0;", 1, 1, "const_with_embedded_lex_error"),
        ("co@nt X real = .14;", 1, 3, "invalid_symbol_but_parser_continues"),
        ("3.14 X: real = 1.0;", 0, 5, "number_before_name_no_const"),
        ("const real: real = 1.0;", 0, 3, "type_used_as_name"),
        ("abc real = 1.0;", 0, 2, "no_const_two_identifiers"),
        ("100 X: real = 1.0;", 0, 6, "number_before_identifier"),
        ("const ; X: real = 1.0;", 0, 6, "stray_semicolon_before_name"),
        ("const ;; X: real = 1.0;", 0, 7, "double_semicolon_before_name"),
        ("; X: real = 1.0;", 0, 7, "leading_spurious_semicolon"),
        ("const const X: real = 1.0;", 0, 1, "duplicate_const_as_name"),
        ("const X A: real = 1.0;", 0, 1, "extra_identifier_before_colon"),
        ("const X real = 1.0;", 0, 1, "missing_colon"),
        ("const X:= real = 1.0;", 0, 2, "assign_operator_instead_of_colon"),
        ("const X: = 1.0;", 0, 1, "missing_real"),
        ("const X: real 1.0;", 0, 1, "missing_equal"),
        ("const X: real = ;", 0, 1, "missing_number"),
        ("const X: real ;= 1.0;", 0, 3, "semicolon_before_equal"),
        ("const X: real = ;1.0;", 0, 2, "semicolon_before_number"),
        ("const X: real = 1.0", 0, 1, "missing_final_semicolon"),
        ("const X:: real = 1.0;", 0, 1, "double_colon"),
        ("const X: real == 1.0;", 0, 1, "double_equal"),
        ("const X: real = 1.0;;", 0, 1, "double_semicolon"),
        ("const X: real = 3;", 0, 1, "integer_where_float_expected"),
        ("const X: real = 3.k4;", 0, 1, "bad_float_with_suffix"),
        ("const X: real = .;", 1, 1, "dot_literal_lex_and_syntax"),
        ("const X: real = 1.0; ???", 1, 1, "trailing_garbage"),
        ("??? garbage", 1, 6, "unexpected_sequence"),
    ]

    for src, exp_lex, exp_syn, label in cases:
        lex, syn = _analyze(src)
        assert lex == exp_lex, f"{label}: lex {lex} != {exp_lex}\n{src!r}"
        assert syn == exp_syn, f"{label}: syn {syn} != {exp_syn}\n{src!r}"

    print("test_parser_matrix: OK (%d cases)" % len(cases))


if __name__ == "__main__":
    main()
