"""Локальные оптимизации трёхадресного кода (TAC) и тетрад выражений."""

from typing import Dict, List, Optional, TYPE_CHECKING

from ast_semantic import SymbolTable
from ir_codegen import TAC

if TYPE_CHECKING:
    from expr_parser import Quad


def _is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _format_float(value: float) -> str:
    text = f"{value:g}"
    if "." not in text and "e" not in text.lower():
        return f"{text}.0"
    return text


class OptimizationResult:
    def __init__(self, name: str, description: str, before: List[TAC], after: List[TAC]):
        self.name = name
        self.description = description
        self.before = before
        self.after = after


def constant_folding(instructions: List[TAC]) -> List[TAC]:
    """
    Оптимизация 1: свёртка констант.
    Вычисляет унарный минус над числовым литералом на этапе компиляции.
    Пример: t1 = -3.14  →  t1 = -3.14 (assign) или прямая подстановка в assign.
    """
    out: List[TAC] = []
    for ins in instructions:
        if ins.op == "uminus" and _is_numeric(ins.arg1):
            folded = _format_float(-float(ins.arg1))
            out.append(TAC("assign", folded, "", ins.result))
            continue
        out.append(TAC(ins.op, ins.arg1, ins.arg2, ins.result))
    return out


def copy_propagation(instructions: List[TAC], symbol_table: Optional[SymbolTable] = None) -> List[TAC]:
    """
    Оптимизация 2: распространение копий и констант.
    - Подставляет известные значения констант вместо идентификаторов.
    - Устраняет лишние временные переменные (t1 = 3.14; pi = t1 → pi = 3.14).
    """
    const_values: Dict[str, str] = {}
    if symbol_table:
        for name, sym in symbol_table.symbols.items():
            if sym.value is not None:
                const_values[name] = _format_float(sym.value)

    temp_values: Dict[str, str] = {}
    out: List[TAC] = []

    def resolve(src: str) -> str:
        if src in temp_values:
            return temp_values[src]
        if src in const_values:
            return const_values[src]
        return src

    for ins in instructions:
        if ins.op == "declare":
            out.append(TAC(ins.op, ins.arg1, ins.arg2, ins.result))
            continue

        if ins.op == "copy":
            resolved = resolve(ins.arg1)
            if resolved != ins.arg1 and _is_numeric(resolved):
                out.append(TAC("assign", resolved, "", ins.result))
                temp_values[ins.result] = resolved
            else:
                out.append(TAC(ins.op, ins.arg1, ins.arg2, ins.result))
                if ins.result.startswith("t"):
                    temp_values[ins.result] = ins.arg1
            continue

        if ins.op in ("assign", "uminus"):
            src = resolve(ins.arg1) if ins.op == "assign" else ins.arg1
            if ins.op == "uminus":
                if _is_numeric(src):
                    folded = _format_float(-float(src))
                    out.append(TAC("assign", folded, "", ins.result))
                    if ins.result.startswith("t"):
                        temp_values[ins.result] = folded
                    continue
                out.append(TAC(ins.op, ins.arg1, ins.arg2, ins.result))
                continue

            if _is_numeric(src) or src in const_values:
                final_src = resolve(src)
                out.append(TAC("assign", final_src, "", ins.result))
                if ins.result.startswith("t"):
                    temp_values[ins.result] = final_src
            else:
                out.append(TAC(ins.op, src, ins.arg2, ins.result))
            continue

        out.append(TAC(ins.op, ins.arg1, ins.arg2, ins.result))

    return _eliminate_temp_chains(out)


def _eliminate_temp_chains(instructions: List[TAC]) -> List[TAC]:
    """t1 = 3.14; pi = t1  →  pi = 3.14"""
    temp_to_const: Dict[str, str] = {}
    out: List[TAC] = []

    for ins in instructions:
        if ins.op == "assign" and ins.result.startswith("t") and _is_numeric(ins.arg1):
            temp_to_const[ins.result] = ins.arg1
            out.append(ins)
            continue

        if ins.op == "assign" and ins.arg1 in temp_to_const:
            out.append(TAC("assign", temp_to_const[ins.arg1], "", ins.result))
            continue

        out.append(ins)

    return _remove_unused_temps(out)


def _remove_unused_temps(instructions: List[TAC]) -> List[TAC]:
    used_temps = set()
    for ins in instructions:
        if ins.op == "assign" and ins.arg1.startswith("t"):
            used_temps.add(ins.arg1)

    result: List[TAC] = []
    for ins in instructions:
        if ins.result.startswith("t") and ins.result not in used_temps:
            continue
        result.append(ins)
    return result


def apply_optimizations(
    instructions: List[TAC], symbol_table: Optional[SymbolTable] = None
) -> List[OptimizationResult]:
    """Последовательно применяет две локальные оптимизации, возвращая промежуточные IR."""
    ir0 = [TAC(i.op, i.arg1, i.arg2, i.result) for i in instructions]
    ir1 = constant_folding(ir0)
    ir2 = copy_propagation(ir1, symbol_table)

    return _build_tac_optimization_results(ir0, ir1, ir2)


def _build_tac_optimization_results(ir0: List[TAC], ir1: List[TAC], ir2: List[TAC]) -> List[OptimizationResult]:
    return [
        OptimizationResult(
            "Свёртка констант",
            "Вычисление унарного минуса над числовым литералом на этапе компиляции "
            "(t = -3.14 → t = -3.14 как прямое присваивание).",
            ir0,
            ir1,
        ),
        OptimizationResult(
            "Распространение копий",
            "Подстановка известных значений констант и устранение лишних временных "
            "(t1 = a при известном a; pi = t1 → pi = 3.14).",
            ir1,
            ir2,
        ),
    ]


def _is_int_literal(value: str) -> bool:
    return value.lstrip("-").isdigit()


def _eval_binop(op: str, a: int, b: int) -> Optional[int]:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            return None
        return a // b
    return None


def format_quads(quads: List["Quad"]) -> str:
    if not quads:
        return "(пусто)"
    lines = []
    for i, q in enumerate(quads, 1):
        lines.append(f"{i}. ({q.op}, {q.arg1}, {q.arg2}, {q.result})")
    return "\n".join(lines)


def fold_quad_constants(quads: List["Quad"]) -> List["Quad"]:
    """Свёртка констант в тетрадах: (+, 2, 3, t1) → (=, 5, , t1)."""
    from expr_parser import Quad

    temp_vals: Dict[str, str] = {}
    out: List[Quad] = []
    for q in quads:
        arg1 = temp_vals.get(q.arg1, q.arg1)
        arg2 = temp_vals.get(q.arg2, q.arg2)

        if (
            q.op in ("+", "-", "*", "/")
            and _is_int_literal(arg1)
            and _is_int_literal(arg2)
        ):
            value = _eval_binop(q.op, int(arg1), int(arg2))
            if value is not None:
                folded = str(value)
                out.append(Quad("=", folded, "", q.result))
                temp_vals[q.result] = folded
                continue

        if q.op == "=" and _is_int_literal(arg1):
            out.append(Quad("=", arg1, "", q.result))
            temp_vals[q.result] = arg1
            continue

        out.append(Quad(q.op, arg1, arg2, q.result))
    return out


def algebraic_quad_simplify(quads: List["Quad"]) -> List["Quad"]:
    """Упрощение: x+0, x-0, x*1, x/1 → копирование операнда."""
    from expr_parser import Quad

    out: List[Quad] = []
    for q in quads:
        if q.op == "+" and q.arg2 == "0":
            out.append(Quad("=", q.arg1, "", q.result))
            continue
        if q.op == "+" and q.arg1 == "0":
            out.append(Quad("=", q.arg2, "", q.result))
            continue
        if q.op == "-" and q.arg2 == "0":
            out.append(Quad("=", q.arg1, "", q.result))
            continue
        if q.op == "*" and (q.arg1 == "1" or q.arg2 == "1"):
            src = q.arg2 if q.arg1 == "1" else q.arg1
            out.append(Quad("=", src, "", q.result))
            continue
        if q.op == "/" and q.arg2 == "1":
            out.append(Quad("=", q.arg1, "", q.result))
            continue
        out.append(Quad(q.op, q.arg1, q.arg2, q.result))
    return out


def apply_quad_optimizations(quads: List["Quad"]) -> List[OptimizationResult]:
    from expr_parser import Quad

    ir0 = [Quad(q.op, q.arg1, q.arg2, q.result) for q in quads]
    ir1 = fold_quad_constants(ir0)
    ir2 = algebraic_quad_simplify(ir1)
    return [
        OptimizationResult(
            "Свёртка констант (тетрады)",
            "Вычисление операций над целочисленными литералами на этапе компиляции.",
            ir0,
            ir1,
        ),
        OptimizationResult(
            "Алгебраическое упрощение (тетрады)",
            "Замена x+0, x*1, x/1 и т.п. на прямое присваивание (=, x, , t).",
            ir1,
            ir2,
        ),
    ]
