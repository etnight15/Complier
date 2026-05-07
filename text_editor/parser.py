from typing import List, Tuple
import re
from scanner import Token, TokenType


class SyntaxError:
    def __init__(self, fragment: str, line: int, pos: int, message: str):
        self.fragment = fragment
        self.line = line
        self.pos = pos
        self.message = message


class Parser:
    def __init__(self):
        self.tokens = []
        self.index = 0
        self.errors = []
        
    def reset(self):
        self.index = 0
        self.errors = []
    
    def current(self):
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None
    
    def next(self):
        if self.index < len(self.tokens):
            self.index += 1
            return self.current()
        return None
    
    def add_error(self, token, message):
        if token:
            self.errors.append(SyntaxError(token.value, token.line, token.start_pos, message))
        else:
            if self.tokens:
                last = self.tokens[-1]
                self.errors.append(SyntaxError("<конец>", last.line, last.end_pos + 1, message))
            else:
                self.errors.append(SyntaxError("<конец>", 1, 1, message))
    
    def match(self, token_type, value=None):
        token = self.current()
        if token and token.type == token_type and (value is None or token.value == value):
            self.next()
            return True
        return False

    def _consume_repeats(self, token_type):
        count = 0
        first = None
        while self.current() and self.current().type == token_type:
            if count == 0:
                first = self.current()
            count += 1
            self.next()
        return count, first

    def _skip_until(self, stop_types):
        while self.current() and self.current().type not in stop_types:
            self.next()

    def _has_token_ahead(self, token_type):
        return any(t.type == token_type for t in self.tokens[self.index:])

    def _is_const_typo(self, value: str) -> bool:
        if not value:
            return False
        target = "const"
        s = value.lower()
        m, n = len(s), len(target)
        if abs(m - n) > 2:
            return False
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s[i - 1] == target[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )
        return dp[m][n] <= 2

    def _find_error_near_start(self):
        stop_types = {
            TokenType.SEPARATOR_COLON,
            TokenType.OPERATOR_ASSIGN,
            TokenType.OPERATOR_EQUAL,
            TokenType.SEPARATOR_SEMICOLON,
        }
        idx = self.index
        while idx < len(self.tokens):
            token = self.tokens[idx]
            if token.type in stop_types:
                break
            if token.type == TokenType.ERROR:
                return token
            idx += 1
        return None

    def _format_invalid_symbol(self, value: str) -> str:
        if value and len(value) > 1 and all(ch == value[0] for ch in value):
            return f"недопустимый символ '{value[0]}' (повторение: {len(value)} раза)"
        return f"недопустимый символ '{value}'"

    def _rewind_to_identifier_before_colon(self):
        last_identifier_idx = None
        idx = self.index
        while idx < len(self.tokens):
            token = self.tokens[idx]
            if token.type == TokenType.SEPARATOR_COLON:
                break
            if token.type == TokenType.SEPARATOR_SEMICOLON:
                break
            if token.type == TokenType.IDENTIFIER:
                last_identifier_idx = idx
            idx += 1
        if last_identifier_idx is not None:
            self.index = last_identifier_idx
    
    def analyze(self, tokens: List[Token]) -> Tuple[bool, List[SyntaxError]]:
        self.tokens = [t for t in tokens if t.type not in [TokenType.WHITESPACE, TokenType.NEWLINE]]
        self.reset()
        
        if not self.tokens:
            self.add_error(None, "Пустая строка")
            return False, self.errors
        
        has_error = False
        suppress_missing_identifier_error = False
        
        # Для корректного восстановления и без каскадных ложных ошибок:
        # если начало объявления не распознано как `const`, считаем конструкцию
        # несоответствующей грамматике и выдаем только одну целевую ошибку.
        if not self.match(TokenType.KEYWORD_CONST, 'const'):
            near_error = self._find_error_near_start()
            if near_error:
                self.add_error(
                    self.current(),
                    f"Ожидалось ключевое слово const ({self._format_invalid_symbol(near_error.value)})",
                )
                has_error = True
                suppress_missing_identifier_error = True
                self._rewind_to_identifier_before_colon()
            else:
                self.add_error(self.current(), "Ожидалось ключевое слово const")
            has_error = True

            token = self.current()

        extra_const_count = 0
        while self.current() and self.current().type == TokenType.KEYWORD_CONST:
            if self.current().value == "const":
                extra_const_count += 1
            self.next()
        if extra_const_count > 0:
            self.add_error(self.current(), "Лишнее ключевое слово 'const' перед идентификатором")
            has_error = True

        if not self.match(TokenType.IDENTIFIER):
            if not suppress_missing_identifier_error:
                self.add_error(self.current(), "Отсутствует идентификатор")
                has_error = True
            self._skip_until({
                TokenType.IDENTIFIER,
                TokenType.SEPARATOR_COLON,
                TokenType.OPERATOR_ASSIGN,
                TokenType.KEYWORD_REAL,
                TokenType.OPERATOR_EQUAL,
                TokenType.NUMBER,
                TokenType.SEPARATOR_SEMICOLON,
            })
            self.match(TokenType.IDENTIFIER)
        else:
            if self.current() and self.current().type == TokenType.IDENTIFIER:
                ahead_has_colon = any(
                    t.type == TokenType.SEPARATOR_COLON for t in self.tokens[self.index:]
                )
                if ahead_has_colon:
                    self.add_error(self.current(), "Лишний идентификатор перед ':'")
                    has_error = True
                    self._skip_until({TokenType.SEPARATOR_COLON})

        if self.current() and self.current().type == TokenType.OPERATOR_ASSIGN:
            self.add_error(self.current(), "Ожидалось ':' (найдено ':=')")
            has_error = True
            self.next()

        colon_count, colon_start = self._consume_repeats(TokenType.SEPARATOR_COLON)
        if colon_count == 0:
            self.add_error(self.current(), "Отсутствует ':'")
            has_error = True
            self._skip_until({
                TokenType.SEPARATOR_COLON,
                TokenType.KEYWORD_REAL,
                TokenType.OPERATOR_EQUAL,
                TokenType.NUMBER,
                TokenType.SEPARATOR_SEMICOLON,
            })
            colon_count, colon_start = self._consume_repeats(TokenType.SEPARATOR_COLON)
        elif colon_count > 1:
            self.add_error(colon_start, f"Повторяющийся ':' ({colon_count} раза)")
            has_error = True

        if not self.match(TokenType.KEYWORD_REAL, 'real'):
            self.add_error(self.current(), "Отсутствует 'real'")
            has_error = True
            self._skip_until({
                TokenType.KEYWORD_REAL,
                TokenType.OPERATOR_EQUAL,
                TokenType.NUMBER,
                TokenType.SEPARATOR_SEMICOLON,
            })
            self.match(TokenType.KEYWORD_REAL, 'real')

        equal_count, equal_start = self._consume_repeats(TokenType.OPERATOR_EQUAL)
        if equal_count == 0:
            self.add_error(self.current(), "Отсутствует '='")
            has_error = True
            self._skip_until({
                TokenType.OPERATOR_EQUAL,
                TokenType.SIGN,
                TokenType.NUMBER,
                TokenType.SEPARATOR_SEMICOLON,
            })
            equal_count, equal_start = self._consume_repeats(TokenType.OPERATOR_EQUAL)
        elif equal_count > 1:
            self.add_error(equal_start, f"Повторяющийся '=' ({equal_count} раза)")
            has_error = True

        self.match(TokenType.SIGN)

        token = self.current()
        if token and token.type == TokenType.NUMBER:
            if not re.fullmatch(r"\d+\.\d+", token.value):
                self.add_error(token, "Ожидалось вещественное число")
                has_error = True
            self.next()
        else:
            self.add_error(token, "Отсутствует число")
            has_error = True
            self._skip_until({TokenType.NUMBER, TokenType.SEPARATOR_SEMICOLON})
            if self.current() and self.current().type == TokenType.NUMBER:
                token = self.current()
                if not re.fullmatch(r"\d+\.\d+", token.value):
                    self.add_error(token, "Ожидалось вещественное число")
                    has_error = True
                self.next()

        semicolon_count, semicolon_start = self._consume_repeats(TokenType.SEPARATOR_SEMICOLON)
        if semicolon_count == 0:
            # Если ';' существует дальше в строке, не дублируем ложную ошибку
            # "Отсутствует ';'" при уже зафиксированной ошибке формата числа.
            if not self._has_token_ahead(TokenType.SEPARATOR_SEMICOLON):
                self.add_error(self.current(), "Отсутствует ';'")
                has_error = True
            else:
                self._skip_until({TokenType.SEPARATOR_SEMICOLON})
                semicolon_count, semicolon_start = self._consume_repeats(TokenType.SEPARATOR_SEMICOLON)
        elif semicolon_count > 1:
            self.add_error(semicolon_start, f"Повторяющийся ';' ({semicolon_count} раза)")
            has_error = True

        if self.index < len(self.tokens):
            self.add_error(self.current(), "Лишние символы после объявления")
            has_error = True
        
        return not has_error, self.errors


ParserV2 = Parser