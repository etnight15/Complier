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
    
    def analyze(self, tokens: List[Token]) -> Tuple[bool, List[SyntaxError]]:
        self.tokens = [t for t in tokens if t.type not in [TokenType.WHITESPACE, TokenType.NEWLINE]]
        self.reset()
        
        if not self.tokens:
            self.add_error(None, "Пустая строка")
            return False, self.errors
        
        has_error = False
        
        if not self.match(TokenType.KEYWORD_CONST, 'const'):
            self.add_error(self.current(), "Отсутствует 'const'")
            has_error = True
            if not self.current() or (self.current() and self.current().type == TokenType.SEPARATOR_SEMICOLON):
                return False, self.errors
            self._skip_until({TokenType.KEYWORD_CONST, TokenType.IDENTIFIER, TokenType.SEPARATOR_COLON, TokenType.OPERATOR_ASSIGN, TokenType.OPERATOR_EQUAL, TokenType.SEPARATOR_SEMICOLON, TokenType.NUMBER, TokenType.SIGN})
            self.match(TokenType.KEYWORD_CONST, 'const')

        if not self.match(TokenType.IDENTIFIER):
            self.add_error(self.current(), "Отсутствует идентификатор")
            has_error = True
            self._skip_until({TokenType.IDENTIFIER, TokenType.SEPARATOR_COLON, TokenType.OPERATOR_ASSIGN, TokenType.OPERATOR_EQUAL, TokenType.SEPARATOR_SEMICOLON})
            self.match(TokenType.IDENTIFIER)

        if self.current() and self.current().type == TokenType.OPERATOR_ASSIGN:
            self.add_error(self.current(), "Ожидалось ':' (найдено ':=')")
            has_error = True
            self.next()

        colon_count, colon_start = self._consume_repeats(TokenType.SEPARATOR_COLON)
        if colon_count == 0:
            self.add_error(self.current(), "Отсутствует ':'")
            has_error = True
            self._skip_until({TokenType.SEPARATOR_COLON, TokenType.KEYWORD_REAL, TokenType.OPERATOR_EQUAL, TokenType.SEPARATOR_SEMICOLON})
            colon_count, colon_start = self._consume_repeats(TokenType.SEPARATOR_COLON)
        elif colon_count > 1:
            self.add_error(colon_start, f"Повторяющийся ':' ({colon_count} раза)")
            has_error = True

        if not self.match(TokenType.KEYWORD_REAL, 'real'):
            self.add_error(self.current(), "Отсутствует 'real'")
            has_error = True
            self._skip_until({TokenType.KEYWORD_REAL, TokenType.OPERATOR_EQUAL, TokenType.SEPARATOR_SEMICOLON})
            self.match(TokenType.KEYWORD_REAL, 'real')

        equal_count, equal_start = self._consume_repeats(TokenType.OPERATOR_EQUAL)
        if equal_count == 0:
            self.add_error(self.current(), "Отсутствует '='")
            has_error = True
            self._skip_until({TokenType.OPERATOR_EQUAL, TokenType.SIGN, TokenType.NUMBER, TokenType.SEPARATOR_SEMICOLON})
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
                self.next()

        semicolon_count, semicolon_start = self._consume_repeats(TokenType.SEPARATOR_SEMICOLON)
        if semicolon_count == 0:
            self.add_error(self.current(), "Отсутствует ';'")
            has_error = True
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