from enum import Enum, auto
from typing import List, Tuple, Optional


class TokenType(Enum):
    """Типы лексем для объявления вещественной константы в Pascal"""
    KEYWORD_CONST = auto()      # const
    KEYWORD_REAL = auto()       # real
    IDENTIFIER = auto()         # идентификатор (pi)
    OPERATOR_ASSIGN = auto()    # :=
    OPERATOR_EQUAL = auto()     # =
    SEPARATOR_COLON = auto()    # :
    SEPARATOR_SEMICOLON = auto() # ;
    NUMBER = auto()             # вещественное число (3.14)
    WHITESPACE = auto()         # пробелы, табуляции
    NEWLINE = auto()            # перевод строки
    ERROR = auto()              # ошибочный символ
    UNKNOWN = auto()            # неизвестный тип


class Token:
    """Класс, представляющий лексему"""
    
    def __init__(self, token_type: TokenType, value: str, line: int, start_pos: int, end_pos: int):
        self.type = token_type
        self.value = value
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos
        
    def get_type_code(self) -> int:
        """Получить числовой код типа лексемы"""
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
        """Получить текстовое описание типа лексемы"""
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
    """Лексический анализатор для объявления вещественной константы в Pascal"""
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.errors: List[Token] = []
        self.current_line = 1
        self.current_pos = 1
        
    def reset(self):
        """Сброс состояния анализатора"""
        self.tokens = []
        self.errors = []
        self.current_line = 1
        self.current_pos = 1
        
    def analyze(self, text: str) -> Tuple[List[Token], List[Token]]:
        """
        Анализ входного текста
        
        Args:
            text: входная строка для анализа
            
        Returns:
            Кортеж (токены, ошибки)
        """
        self.reset()
        
        i = 0
        length = len(text)
        
        while i < length:
            ch = text[i]
            
            # Обработка перевода строки
            if ch == '\n':
                self.tokens.append(Token(
                    TokenType.NEWLINE, ch, 
                    self.current_line, self.current_pos, self.current_pos
                ))
                self.current_line += 1
                self.current_pos = 1
                i += 1
                continue
            
            # Обработка пробелов и табуляции
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
            
            # Проверка ключевых слов и идентификаторов
            if ch.isalpha() or ch == '_':
                start_pos = self.current_pos
                start_i = i
                while i < length and (text[i].isalnum() or text[i] == '_'):
                    i += 1
                    self.current_pos += 1
                value = text[start_i:i]
                
                # Проверка на ключевые слова
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
            
            # Проверка чисел (включая вещественные)
            if ch.isdigit() or ch == '.':
                start_pos = self.current_pos
                start_i = i
                has_dot = False
                valid = True
                
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
                
                # Проверка на корректность числа
                if has_dot and value != '.' and value[-1] != '.':
                    self.tokens.append(Token(
                        TokenType.NUMBER, value,
                        self.current_line, start_pos, self.current_pos - 1
                    ))
                else:
                    # Ошибочное число
                    error_token = Token(
                        TokenType.ERROR, value,
                        self.current_line, start_pos, self.current_pos - 1
                    )
                    self.tokens.append(error_token)
                    self.errors.append(error_token)
                continue
            
            # Проверка операторов и разделителей
            if ch == ':':
                start_pos = self.current_pos
                i += 1
                self.current_pos += 1
                
                # Проверка на оператор :=
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
            
            # Обработка недопустимых символов
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
    
    def validate_syntax(self, tokens: List[Token]) -> List[str]:
        """
        Проверка синтаксической корректности объявления константы
        
        Ожидаемая последовательность:
        const <идентификатор> : real = <число> ;
        """
        syntax_errors = []
        
        # Фильтруем пробелы и переводы строк для проверки структуры
        important_tokens = [t for t in tokens if t.type not in [TokenType.WHITESPACE, TokenType.NEWLINE]]
        
        expected_sequence = [
            TokenType.KEYWORD_CONST,
            TokenType.IDENTIFIER,
            TokenType.SEPARATOR_COLON,
            TokenType.KEYWORD_REAL,
            TokenType.OPERATOR_EQUAL,
            TokenType.NUMBER,
            TokenType.SEPARATOR_SEMICOLON
        ]
        
        if len(important_tokens) < len(expected_sequence):
            syntax_errors.append(f"Строка {self.current_line}: Неполное объявление константы")
            return syntax_errors
        
        for i, expected_type in enumerate(expected_sequence):
            if i >= len(important_tokens):
                syntax_errors.append(f"Строка {self.current_line}: Ожидался {expected_type.name}")
                break
                
            if important_tokens[i].type != expected_type:
                syntax_errors.append(
                    f"Строка {important_tokens[i].line}, позиция {important_tokens[i].start_pos}: "
                    f"Ожидался {expected_type.name}, найден {important_tokens[i].type.name}"
                )
        
        # Проверка наличия лишних токенов после точки с запятой
        if len(important_tokens) > len(expected_sequence):
            extra_tokens = important_tokens[len(expected_sequence):]
            for token in extra_tokens:
                if token.type not in [TokenType.WHITESPACE, TokenType.NEWLINE]:
                    syntax_errors.append(
                        f"Строка {token.line}, позиция {token.start_pos}: "
                        f"Лишний токен '{token.value}' после объявления"
                    )
        
        return syntax_errors