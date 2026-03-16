from enum import Enum, auto
from typing import List, Tuple


class TokenType(Enum):
    KEYWORD_CONST = auto()
    KEYWORD_REAL = auto()
    IDENTIFIER = auto()
    OPERATOR_ASSIGN = auto()
    OPERATOR_EQUAL = auto()
    SEPARATOR_COLON = auto()
    SEPARATOR_SEMICOLON = auto()
    NUMBER = auto()
    WHITESPACE = auto()
    NEWLINE = auto()
    ERROR = auto()
    UNKNOWN = auto()


class Token:
    
    def __init__(self, token_type: TokenType, value: str, line: int, start_pos: int, end_pos: int):
        self.type = token_type
        self.value = value
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos
        
    def get_type_code(self) -> int:
        codes = {
            TokenType.KEYWORD_CONST: 1,
            TokenType.KEYWORD_REAL: 2,
            TokenType.IDENTIFIER: 3,
            TokenType.OPERATOR_ASSIGN: 4,
            TokenType.OPERATOR_EQUAL: 5,
            TokenType.SEPARATOR_COLON: 6,
            TokenType.SEPARATOR_SEMICOLON: 7,
            TokenType.NUMBER: 8,
            TokenType.WHITESPACE: 9,
            TokenType.NEWLINE: 10,
            TokenType.ERROR: 99,
            TokenType.UNKNOWN: 0
        }
        return codes.get(self.type, 0)
    
    def get_type_name(self) -> str:
        names = {
            TokenType.KEYWORD_CONST: "Ключевое слово 'const'",
            TokenType.KEYWORD_REAL: "Ключевое слово 'real'",
            TokenType.IDENTIFIER: "Идентификатор",
            TokenType.OPERATOR_ASSIGN: "Оператор присваивания",
            TokenType.OPERATOR_EQUAL: "Оператор равенства",
            TokenType.SEPARATOR_COLON: "Разделитель ':'",
            TokenType.SEPARATOR_SEMICOLON: "Разделитель ';'",
            TokenType.NUMBER: "Вещественное число",
            TokenType.WHITESPACE: "Пробельный символ",
            TokenType.NEWLINE: "Перевод строки",
            TokenType.ERROR: "Ошибка",
            TokenType.UNKNOWN: "Неизвестный тип"
        }
        return names.get(self.type, "Неизвестный тип")
    
    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', line={self.line}, pos={self.start_pos}-{self.end_pos})"


class Scanner:
    
    def __init__(self):
        self.tokens = []
        self.errors = []
        self.current_line = 1
        self.current_pos = 1
        
    def reset(self):
        self.tokens = []
        self.errors = []
        self.current_line = 1
        self.current_pos = 1
        
    def analyze(self, text: str) -> Tuple[List[Token], List[Token]]:
        self.reset()
        
        i = 0
        length = len(text)
        
        while i < length:
            ch = text[i]
            
            if ch == '\n':
                self.tokens.append(Token(
                    TokenType.NEWLINE, ch, 
                    self.current_line, self.current_pos, self.current_pos
                ))
                self.current_line += 1
                self.current_pos = 1
                i += 1
                continue
            
            if ch.isspace():
                start_pos = self.current_pos
                start_i = i
                while i < length and text[i].isspace() and text[i] != '\n':
                    i += 1
                    self.current_pos += 1
                value = text[start_i:i]
                self.tokens.append(Token(
                    TokenType.WHITESPACE, value,
                    self.current_line, start_pos, self.current_pos - 1
                ))
                continue
            
            if ch.isalpha() or ch == '_':
                start_pos = self.current_pos
                start_i = i
                while i < length and (text[i].isalnum() or text[i] == '_'):
                    i += 1
                    self.current_pos += 1
                value = text[start_i:i]
                
                if value == 'const':
                    token_type = TokenType.KEYWORD_CONST
                elif value == 'real':
                    token_type = TokenType.KEYWORD_REAL
                else:
                    token_type = TokenType.IDENTIFIER
                
                self.tokens.append(Token(
                    token_type, value,
                    self.current_line, start_pos, self.current_pos - 1
                ))
                continue
            
            if ch.isdigit() or ch == '.':
                start_pos = self.current_pos
                start_i = i
                has_dot = False
                
                while i < length:
                    ch = text[i]
                    if ch.isdigit():
                        i += 1
                        self.current_pos += 1
                    elif ch == '.' and not has_dot:
                        has_dot = True
                        i += 1
                        self.current_pos += 1
                    else:
                        break
                
                value = text[start_i:i]
                
                if has_dot and value != '.' and value[-1] != '.':
                    self.tokens.append(Token(
                        TokenType.NUMBER, value,
                        self.current_line, start_pos, self.current_pos - 1
                    ))
                else:
                    error_token = Token(
                        TokenType.ERROR, value,
                        self.current_line, start_pos, self.current_pos - 1
                    )
                    self.tokens.append(error_token)
                    self.errors.append(error_token)
                continue
            
            if ch == ':':
                start_pos = self.current_pos
                i += 1
                self.current_pos += 1
                
                if i < length and text[i] == '=':
                    i += 1
                    self.current_pos += 1
                    self.tokens.append(Token(
                        TokenType.OPERATOR_ASSIGN, ':=',
                        self.current_line, start_pos, self.current_pos - 1
                    ))
                else:
                    self.tokens.append(Token(
                        TokenType.SEPARATOR_COLON, ':',
                        self.current_line, start_pos, self.current_pos - 1
                    ))
                continue
            
            if ch == '=':
                self.tokens.append(Token(
                    TokenType.OPERATOR_EQUAL, '=',
                    self.current_line, self.current_pos, self.current_pos
                ))
                i += 1
                self.current_pos += 1
                continue
            
            if ch == ';':
                self.tokens.append(Token(
                    TokenType.SEPARATOR_SEMICOLON, ';',
                    self.current_line, self.current_pos, self.current_pos
                ))
                i += 1
                self.current_pos += 1
                continue
            
            start_pos = self.current_pos
            start_i = i
            i += 1
            self.current_pos += 1
            value = text[start_i:i]
            
            error_token = Token(
                TokenType.ERROR, value,
                self.current_line, start_pos, self.current_pos - 1
            )
            self.tokens.append(error_token)
            self.errors.append(error_token)
        
        return self.tokens, self.errors