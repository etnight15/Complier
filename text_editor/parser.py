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
    _CONST_LETTERS = frozenset("const")

    def __init__(self):
        self.tokens = []
        self.index = 0
        self.errors = []
        
    def reset(self):
        self.index = 0
        self.errors = []
        self._skip_duplicate_real_msg = False
    
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

    def _prefix_scan_stop_types(self):
        return {
            TokenType.SEPARATOR_COLON,
            TokenType.OPERATOR_ASSIGN,
            TokenType.OPERATOR_EQUAL,
            TokenType.SEPARATOR_SEMICOLON,
        }

    def _looks_like_const_fragment(self, ident: str) -> bool:
        """Обломок ключевого слова const (в т.ч. cons, con…), а не имя вроде «p»."""
        v = ident.lower()
        return "const".startswith(v) and len(v) <= 5

    def _error_belongs_to_next_identifier_not_const(self, err_idx: int) -> bool:
        """ERROR после однобуквенного идентификатора не из «const» — уже другое слово (p@ в p@i)."""
        if err_idx == 0:
            return False
        prev = self.tokens[err_idx - 1]
        if prev.type != TokenType.IDENTIFIER:
            return False
        if len(prev.value) != 1:
            return False
        return prev.value.lower() not in self._CONST_LETTERS

    def _collect_error_chunks_near_start(self) -> List[str]:
        """Только ERROR внутри испорченного «const», без символов из имени константы (p@i)."""
        out: List[str] = []
        idx = 0
        while idx < len(self.tokens):
            t = self.tokens[idx]
            if t.type in self._prefix_scan_stop_types():
                break
            if t.type == TokenType.ERROR:
                if self._error_belongs_to_next_identifier_not_const(idx):
                    break
                out.append(t.value)
                idx += 1
                continue
            idx += 1
        return out

    def _format_invalid_symbol(self, value: str) -> str:
        if value and len(value) > 1 and all(ch == value[0] for ch in value):
            return f"недопустимый символ '{value[0]}' (повторение: {len(value)} раза)"
        return f"недопустимый символ '{value}'"

    def _format_invalid_symbols_in_const_prefix(self, chunks: List[str]) -> str:
        if not chunks:
            return ""
        if len(chunks) == 1:
            return self._format_invalid_symbol(chunks[0])
        parts: List[str] = []
        for c in chunks:
            if c and len(c) > 1 and all(ch == c[0] for ch in c):
                parts.append(f"«{c[0]}» (повторение: {len(c)} раза)")
            else:
                parts.append(f"«{c}»")
        return "недопустимые символы: " + ", ".join(parts)

    def _jump_after_invalid_const(self) -> None:
        """После ошибки в слове const: встать на имя перед ':' или на сам ':'.

        Раньше брали последний идентификатор до ':' по всей строке — из-за этого
        курсор перескакивал на «readddl» и дальнейший разбор шёл не по тексту.
        Отбрасываем пару идентификатор+':' только если идентификатор — хвост после
        ERROR сразу после другого идентификатора (типичный случай con@st → «st»),
        но не «const@ pi», где перед pi тоже ERROR, а до него нет обломка-идентификатора.
        """
        pairs: List[int] = []
        n = len(self.tokens)

        for i in range(n):
            if self.tokens[i].type != TokenType.IDENTIFIER:
                continue
            if i + 1 >= n or self.tokens[i + 1].type != TokenType.ERROR:
                continue
            if self._looks_like_const_fragment(self.tokens[i].value):
                continue
            j = i + 2
            while j < n and self.tokens[j].type == TokenType.IDENTIFIER:
                j += 1
            if j < n and self.tokens[j].type == TokenType.SEPARATOR_COLON:
                self.index = i
                return

        for i in range(n - 1):
            if (
                self.tokens[i].type == TokenType.IDENTIFIER
                and self.tokens[i + 1].type == TokenType.SEPARATOR_COLON
            ):
                pairs.append(i)

        def is_junk_suffix(ident_idx: int) -> bool:
            """Только хвост con@st → «st»/«t», не буква имени после @ (например i в p@i)."""
            if ident_idx == 0:
                return False
            if self.tokens[ident_idx - 1].type != TokenType.ERROR:
                return False
            ident = self.tokens[ident_idx]
            if ident.type != TokenType.IDENTIFIER:
                return False
            if ident.value.lower() not in ("st", "t"):
                return False
            for j in range(0, ident_idx - 1):
                if self.tokens[j].type == TokenType.IDENTIFIER:
                    return True
            return False

        good = [i for i in pairs if not is_junk_suffix(i)]
        if good:
            self.index = good[-1]
            return

        if pairs:
            self.index = pairs[-1] + 1
            return

        for i in range(n - 1):
            if (
                self.tokens[i].type == TokenType.IDENTIFIER
                and self.tokens[i + 1].type == TokenType.KEYWORD_REAL
                and not is_junk_suffix(i)
            ):
                self.index = i
                return

        for i in range(n - 1):
            if self.tokens[i].type != TokenType.IDENTIFIER:
                continue
            if self.tokens[i + 1].type != TokenType.IDENTIFIER:
                continue
            if is_junk_suffix(i):
                continue
            if any(
                t.type == TokenType.SEPARATOR_COLON
                for t in self.tokens[: i + 2]
            ):
                continue
            if not any(
                t.type == TokenType.OPERATOR_EQUAL
                for t in self.tokens[i + 2 :]
            ):
                continue
            self.index = i
            return

        colon_idx = next(
            (i for i, t in enumerate(self.tokens) if t.type == TokenType.SEPARATOR_COLON),
            None,
        )
        if colon_idx is not None:
            self.index = colon_idx

    def analyze(self, tokens: List[Token]) -> Tuple[bool, List[SyntaxError]]:
        self.tokens = [t for t in tokens if t.type not in [TokenType.WHITESPACE, TokenType.NEWLINE]]
        self.reset()
        
        if not self.tokens:
            self.add_error(None, "Пустая строка")
            return False, self.errors
        
        has_error = False

        # Если const испорчен (например con@st), лексер даёт ERROR — прыгаем к имени
        # перед ':' или к ':', чтобы дальше разбирать хвост и не «проглатывать» pi.
        if not self.match(TokenType.KEYWORD_CONST, 'const'):
            err_chunks = self._collect_error_chunks_near_start()
            if err_chunks:
                sym = self._format_invalid_symbols_in_const_prefix(err_chunks)
                self.add_error(
                    self.current(),
                    f"Ожидалось ключевое слово const ({sym})",
                )
                has_error = True
                self._jump_after_invalid_const()
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
            tok = self.current()
            if tok and tok.type == TokenType.ERROR:
                if (
                    self.index > 0
                    and self.tokens[self.index - 1].type == TokenType.KEYWORD_CONST
                ):
                    self.add_error(
                        tok,
                        f"Ожидался идентификатор; {self._format_invalid_symbol(tok.value)}",
                    )
                has_error = True
            elif tok and tok.type == TokenType.SEPARATOR_COLON:
                self.add_error(tok, "Отсутствует идентификатор перед ':'")
                has_error = True
            elif tok is None:
                self.add_error(None, "Отсутствует идентификатор")
                has_error = True
            else:
                self.add_error(
                    tok,
                    f"Ожидался идентификатор; найдено «{tok.value}»",
                )
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
            ct = self.current()
            if ct and ct.type == TokenType.KEYWORD_REAL:
                self.add_error(
                    ct,
                    "Пропущено ':' между идентификатором и типом данных real",
                )
            elif ct and ct.type == TokenType.IDENTIFIER:
                prev_tok = self.tokens[self.index - 1] if self.index > 0 else None
                if prev_tok and prev_tok.type == TokenType.IDENTIFIER:
                    self.add_error(prev_tok, "Пропущено ':' после идентификатора")
                    self.add_error(
                        ct,
                        f"Ожидался тип данных real (найдено «{ct.value}»)",
                    )
                else:
                    self.add_error(
                        ct,
                        "Пропущено ':' между идентификатором и типом данных real; "
                        f"ожидалось ключевое слово «real», найдено «{ct.value}»",
                    )
                self._skip_duplicate_real_msg = True
            elif (
                ct
                and ct.type == TokenType.ERROR
                and self.index > 0
                and self.tokens[self.index - 1].type == TokenType.IDENTIFIER
            ):
                self.add_error(
                    ct,
                    f"Ожидался идентификатор; {self._format_invalid_symbol(ct.value)}",
                )
            elif ct and ct.type == TokenType.ERROR:
                self.add_error(
                    ct,
                    f"Недопустимый символ ({self._format_invalid_symbol(ct.value)}); ожидалось ':'",
                )
            else:
                self.add_error(ct, "Отсутствует ':'")
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
            rt = self.current()
            if (
                self._skip_duplicate_real_msg
                and rt
                and rt.type == TokenType.OPERATOR_EQUAL
            ):
                self._skip_duplicate_real_msg = False
                has_error = True
            elif rt is not None:
                self.add_error(rt, "Ожидался тип данных real")
                has_error = True
            else:
                self.add_error(None, "Ожидался тип данных real")
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