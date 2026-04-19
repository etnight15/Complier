import re
from typing import List, Tuple


class SearchResult:
    def __init__(self, match: str, line: int, start_pos: int, end_pos: int, length: int):
        self.match = match
        self.line = line
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.length = length
    
    def __repr__(self):
        return f"SearchResult('{self.match}', line={self.line}, pos={self.start_pos}, len={self.length})"


class SearchEngine:
    
    PATTERNS = {
        1: {
            "name": "Французские номера телефонов",
            "pattern": r"^0[1-9](?:[\s.-]*\d{2}){4}$",
            "description": "Французский номер телефона: начинается с 0, затем цифра от 1 до 9, затем 8 цифр",
            "example": "0612345678"
        },
        2: {
            "name": "Переменные в стиле snake_case",
            "pattern": r"\b[a-z]+_[a-z]+(?:_[a-z]+)*\b",
            "description": "snake_case: только строчные буквы и подчеркивания, минимум два слова",
            "example": "my_variable, user_name, first_last_name"
        },
        3: {
            "name": "Надежный пароль",
            "pattern": r"^(?=.*[А-ЯЁ])(?=.*[а-яё])(?=.*\d)(?=.*[()#?!|/@$%^&*\-_.])[А-Яа-яЁё0-9()#?!|/@$%^&*\-_.]{14,}$",
            "description": "Надежный пароль: длина >=14, заглавная русская буква, строчная русская буква, цифра, спецсимвол",
            "example": "ПриветМир123!@#"
        }
    }
    
    def __init__(self):
        self.results = []
    
    def clear(self):
        self.results = []
    
    def get_patterns_list(self):
        return [(key, value["name"]) for key, value in self.PATTERNS.items()]
    
    def get_pattern_info(self, pattern_id: int):
        return self.PATTERNS.get(pattern_id, None)
    
    def find_all_matches(self, text: str, pattern_id: int) -> Tuple[List[SearchResult], int]:
        self.clear()
        
        if not text.strip():
            return [], 0
        
        pattern_info = self.PATTERNS.get(pattern_id)
        if not pattern_info:
            return [], 0
        
        pattern = pattern_info["pattern"]
        
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            if pattern_id == 3:
                matches = re.finditer(pattern, line, re.MULTILINE)
                for match in matches:
                    start_char = match.start() + 1
                    end_char = match.end()
                    self.results.append(SearchResult(
                        match.group(),
                        line_num,
                        start_char,
                        end_char,
                        len(match.group())
                    ))
            elif pattern_id == 1:
                for match in re.finditer(pattern, line):
                    start_char = match.start() + 1
                    end_char = match.end()
                    self.results.append(SearchResult(
                        match.group(),
                        line_num,
                        start_char,
                        end_char,
                        len(match.group())
                    ))
            else:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    start_char = match.start() + 1
                    end_char = match.end()
                    self.results.append(SearchResult(
                        match.group(),
                        line_num,
                        start_char,
                        end_char,
                        len(match.group())
                    ))
        
        return self.results, len(self.results)