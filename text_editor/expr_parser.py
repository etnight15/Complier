from dataclasses import dataclass
from typing import List, Optional, Tuple

from expr_scanner import ExprToken, ExprTokenType


class ExprSyntaxError:
    def __init__(self, fragment: str, line: int, pos: int, message: str):
        self.fragment = fragment
        self.line = line
        self.pos = pos
        self.message = message


@dataclass
class Quad:
    op: str
    arg1: str
    arg2: str
    result: str


class ExprParser:
    """
    Синтаксический анализатор арифметических выражений методом рекурсивного спуска.

    E → TA | A → ε | + TA | - TA
    T → FB | B → ε | * FB | / FB
    F → num | id | (E)
    """

    def __init__(self):
        self.tokens: List[ExprToken] = []
        self.index = 0
        self.errors: List[ExprSyntaxError] = []
        self.quads: List[Quad] = []
        self._temp_counter = 0

    def reset(self) -> None:
        self.index = 0
        self.errors = []
        self.quads = []
        self._temp_counter = 0

    def _new_temp(self) -> str:
        self._temp_counter += 1
        return f"t{self._temp_counter}"

    def _emit(self, op: str, arg1: str, arg2: str, result: str) -> None:
        self.quads.append(Quad(op, arg1, arg2, result))

    def current(self) -> Optional[ExprToken]:
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None

    def _advance(self) -> Optional[ExprToken]:
        token = self.current()
        if token is not None:
            self.index += 1
        return token

    def _add_error(self, token: Optional[ExprToken], message: str) -> None:
        if token:
            self.errors.append(
                ExprSyntaxError(token.value, token.line, token.start_pos, message)
            )
        else:
            if self.tokens:
                last = self.tokens[-1]
                self.errors.append(
                    ExprSyntaxError("<конец>", last.line, last.end_pos + 1, message)
                )
            else:
                self.errors.append(ExprSyntaxError("<конец>", 1, 1, message))

    def _match_types(self, *types: ExprTokenType) -> bool:
        token = self.current()
        if token and token.type in types:
            self._advance()
            return True
        return False

    def _parse_E(self) -> Optional[str]:
        left = self._parse_T()
        if left is None:
            return None
        return self._parse_A(left)

    def _parse_A(self, left: str) -> Optional[str]:
        token = self.current()
        if not token:
            return left

        if token.type == ExprTokenType.PLUS:
            self._advance()
            right = self._parse_T()
            if right is None:
                self._add_error(self.current(), "Пропущен операнд после '+'")
                return left
            result = self._new_temp()
            self._emit("+", left, right, result)
            return self._parse_A(result)

        if token.type == ExprTokenType.MINUS:
            self._advance()
            right = self._parse_T()
            if right is None:
                self._add_error(self.current(), "Пропущен операнд после '-'")
                return left
            result = self._new_temp()
            self._emit("-", left, right, result)
            return self._parse_A(result)

        return left

    def _parse_T(self) -> Optional[str]:
        left = self._parse_F()
        if left is None:
            return None
        return self._parse_B(left)

    def _parse_B(self, left: str) -> Optional[str]:
        token = self.current()
        if not token:
            return left

        if token.type == ExprTokenType.MULT:
            self._advance()
            right = self._parse_F()
            if right is None:
                self._add_error(self.current(), "Пропущен операнд после '*'")
                return left
            result = self._new_temp()
            self._emit("*", left, right, result)
            return self._parse_B(result)

        if token.type == ExprTokenType.DIV:
            self._advance()
            right = self._parse_F()
            if right is None:
                self._add_error(self.current(), "Пропущен операнд после '/'")
                return left
            result = self._new_temp()
            self._emit("/", left, right, result)
            return self._parse_B(result)

        return left

    def _parse_F(self) -> Optional[str]:
        token = self.current()
        if not token:
            self._add_error(None, "Ожидался операнд (число, идентификатор или '(')")
            return None

        if token.type == ExprTokenType.NUMBER:
            self._advance()
            return token.value

        if token.type == ExprTokenType.IDENTIFIER:
            self._advance()
            return token.value

        if token.type == ExprTokenType.LPAREN:
            self._advance()
            inner = self._parse_E()
            if not self._match_types(ExprTokenType.RPAREN):
                self._add_error(self.current(), "Ожидалась закрывающая скобка ')'")
            return inner

        if token.type in (
            ExprTokenType.PLUS,
            ExprTokenType.MINUS,
            ExprTokenType.MULT,
            ExprTokenType.DIV,
            ExprTokenType.RPAREN,
        ):
            self._add_error(token, "Пропущен операнд")
            return None

        self._add_error(token, "Ожидался операнд (число, идентификатор или '(')")
        return None

    def _check_extra_tokens(self) -> None:
        token = self.current()
        if not token:
            return

        if token.type == ExprTokenType.RPAREN:
            self._add_error(token, "Лишняя закрывающая скобка ')'")
            return

        if token.type in (
            ExprTokenType.PLUS,
            ExprTokenType.MINUS,
            ExprTokenType.MULT,
            ExprTokenType.DIV,
        ):
            self._add_error(token, "Пропущен операнд")
            return

        self._add_error(token, f"Недопустимый символ в выражении: '{token.value}'")

    @staticmethod
    def _meaningful_tokens(tokens: List[ExprToken]) -> List[ExprToken]:
        return [t for t in tokens if t.type not in (ExprTokenType.WHITESPACE,)]

    @staticmethod
    def contains_identifier(tokens: List[ExprToken]) -> bool:
        return any(t.type == ExprTokenType.IDENTIFIER for t in tokens)

    @staticmethod
    def build_rpn_dijkstra(tokens: List[ExprToken]) -> List[str]:
        """ПОЛИЗ (алгоритм сортировочной станции Дейкстры). Только для целых чисел."""
        precedence = {
            ExprTokenType.PLUS: 1,
            ExprTokenType.MINUS: 1,
            ExprTokenType.MULT: 2,
            ExprTokenType.DIV: 2,
        }
        output: List[str] = []
        op_stack: List[ExprToken] = []

        for token in ExprParser._meaningful_tokens(tokens):
            if token.type == ExprTokenType.NUMBER:
                output.append(token.value)
            elif token.type == ExprTokenType.LPAREN:
                op_stack.append(token)
            elif token.type == ExprTokenType.RPAREN:
                while op_stack and op_stack[-1].type != ExprTokenType.LPAREN:
                    output.append(op_stack.pop().value)
                if op_stack and op_stack[-1].type == ExprTokenType.LPAREN:
                    op_stack.pop()
            elif token.type in precedence:
                while (
                    op_stack
                    and op_stack[-1].type != ExprTokenType.LPAREN
                    and op_stack[-1].type in precedence
                    and precedence[op_stack[-1].type] >= precedence[token.type]
                ):
                    output.append(op_stack.pop().value)
                op_stack.append(token)

        while op_stack:
            top = op_stack.pop()
            if top.type == ExprTokenType.LPAREN:
                continue
            output.append(top.value)

        return output

    @staticmethod
    def evaluate_rpn(rpn: List[str]) -> int:
        stack: List[int] = []
        for item in rpn:
            if item.lstrip("-").isdigit():
                stack.append(int(item))
                continue
            if len(stack) < 2:
                raise ValueError("Некорректное ПОЛИЗ-выражение")
            b, a = stack.pop(), stack.pop()
            if item == "+":
                stack.append(a + b)
            elif item == "-":
                stack.append(a - b)
            elif item == "*":
                stack.append(a * b)
            elif item == "/":
                if b == 0:
                    raise ZeroDivisionError("Деление на ноль")
                stack.append(a // b)
            else:
                raise ValueError(f"Неизвестный оператор: {item}")
        if len(stack) != 1:
            raise ValueError("Некорректное ПОЛИЗ-выражение")
        return stack[0]

    def parse(self, tokens: List[ExprToken]) -> Tuple[Optional[str], List[Quad], List[ExprSyntaxError]]:
        self.reset()
        self.tokens = self._meaningful_tokens(tokens)

        if not self.tokens:
            self._add_error(None, "Пустое выражение")
            return None, [], self.errors

        result = self._parse_E()
        self._check_extra_tokens()

        if self.errors:
            return None, [], self.errors

        return result, self.quads, []

    def analyze(
        self, tokens: List[ExprToken]
    ) -> Tuple[Optional[str], List[Quad], List[str], Optional[int], List[ExprSyntaxError], str]:
        """
        Полный разбор: тетрады и (при только целых числах) ПОЛИЗ и значение.
        Возвращает: (результат, тетрады, rpn, значение, ошибки, предупреждение).
        """
        if any(t.type == ExprTokenType.ERROR for t in tokens):
            return (
                None,
                [],
                [],
                None,
                [],
                "Генерация тетрад и ПОЛИЗ пропущена: обнаружены лексические ошибки.",
            )

        result, quads, errors = self.parse(tokens)
        warning = ""

        if errors:
            return result, [], [], None, errors, (
                "Генерация тетрад и ПОЛИЗ пропущена: обнаружены синтаксические ошибки."
            )

        meaningful = self._meaningful_tokens(tokens)
        if self.contains_identifier(meaningful):
            warning = (
                "ПОЛИЗ и вычисление значения доступны только для выражений из целых чисел "
                "(без идентификаторов)."
            )
            return result, quads, [], None, [], warning

        try:
            rpn = self.build_rpn_dijkstra(meaningful)
            value = self.evaluate_rpn(rpn)
        except ZeroDivisionError:
            warning = "Деление на ноль при вычислении ПОЛИЗ."
            return result, quads, self.build_rpn_dijkstra(meaningful), None, [], warning
        except ValueError as exc:
            warning = str(exc)
            return result, quads, [], None, [], warning

        return result, quads, rpn, value, [], warning
