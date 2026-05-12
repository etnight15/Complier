from typing import List, Optional, Tuple
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
        self._after_digit_split_name_recovery = False
        self._suppress_next_real_expected_msg = False
        self._absorbed_real_junk_positions = set()
    
    def current(self):
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None
    
    def next(self):
        if self.index < len(self.tokens):
            self.index += 1
            return self.current()
        return None
    
    def add_error(self, token, message, fragment_override=None):
        if token:
            frag = fragment_override if fragment_override is not None else token.value
            self.errors.append(SyntaxError(frag, token.line, token.start_pos, message))
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

    def _recover_after_digit_start_constant_name(self) -> None:
        """После ошибки «имя с цифры» (NUMBER + IDENTIFIER вроде 3pi) пропускаем оба токена,
        чтобы разбирать хвост (: real = …) и не обрывать вывод ошибок."""
        self._after_digit_split_name_recovery = True
        if self.current() and self.current().type == TokenType.NUMBER:
            self.next()
        if self.current() and self.current().type == TokenType.IDENTIFIER:
            self.next()

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
        """Только ERROR внутри испорченного «const», без символов из имени константы (p@i).

        После цепочки «con» + ERROR + «st» ключевое слово уже «замкнуто» — последующие ERROR
        (например второй «!» перед именем константы) в сообщение про const не входят.
        """
        out: List[str] = []
        idx = 0
        closed_con_st_typo = False
        while idx < len(self.tokens):
            t = self.tokens[idx]
            if t.type in self._prefix_scan_stop_types():
                break
            if t.type == TokenType.IDENTIFIER:
                if (
                    t.value.lower() == "st"
                    and idx >= 2
                    and self.tokens[idx - 2].type == TokenType.IDENTIFIER
                    and self.tokens[idx - 2].value.lower() == "con"
                    and self.tokens[idx - 1].type == TokenType.ERROR
                ):
                    closed_con_st_typo = True
                idx += 1
                continue
            if t.type == TokenType.ERROR:
                if self._error_belongs_to_next_identifier_not_const(idx):
                    break
                if closed_con_st_typo:
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

    def _invalid_symbol_message_simple(self, value: str) -> str:
        frag = self._format_invalid_symbol(value)
        if not frag:
            return "Лексическая ошибка: недопустимый символ"
        return f"Лексическая ошибка: {frag}"

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

    def _split_broken_const_spelling(self) -> Tuple[List[str], List[Token], int, bool, bool]:
        """Собирает буквы const; между ними — ERROR, а также = ; : := и знаки, пока слово не собрано.

        Последний флаг: слово «const» завершено лексемой KEYWORD_CONST (мусор только *перед*
        целым ключевым словом), а не склейкой идентификаторов вроде con@st.
        """
        n = len(self.tokens)
        remaining = "const"
        idx = 0
        inside: List[str] = []
        closed_by_keyword_const = False

        while idx < n and remaining:
            t = self.tokens[idx]
            if t.type == TokenType.ERROR:
                inside.append(t.value)
                idx += 1
                continue
            if t.type == TokenType.SIGN:
                inside.append(t.value)
                idx += 1
                continue
            if t.type == TokenType.OPERATOR_EQUAL and t.value == "=":
                inside.append("=")
                idx += 1
                continue
            if t.type == TokenType.SEPARATOR_SEMICOLON:
                inside.append(";")
                idx += 1
                continue
            if t.type == TokenType.SEPARATOR_COLON:
                inside.append(":")
                idx += 1
                continue
            if t.type == TokenType.OPERATOR_ASSIGN:
                inside.append(t.value)
                idx += 1
                continue
            if t.type == TokenType.KEYWORD_CONST and t.value.lower() == "const":
                remaining = ""
                closed_by_keyword_const = True
                idx += 1
                continue
            if t.type == TokenType.IDENTIFIER:
                v = t.value.lower()
                if v == "const":
                    remaining = ""
                    idx += 1
                    continue
                if remaining.startswith(v):
                    remaining = remaining[len(v) :]
                    idx += 1
                    continue
                k = 0
                m = min(len(v), len(remaining))
                while k < m and v[k] == remaining[k]:
                    k += 1
                if k > 0:
                    remaining = remaining[k:]
                    idx += 1
                    continue
                break
            break

        trailing: List[Token] = []
        if remaining == "":
            while idx < n and self.tokens[idx].type == TokenType.ERROR:
                trailing.append(self.tokens[idx])
                idx += 1

        completed = remaining == ""
        return inside, trailing, idx, completed, closed_by_keyword_const

    def _lookahead_has_error_or_sign_before_equal_or_colon(self, from_idx: int) -> bool:
        i = from_idx + 1
        while i < len(self.tokens):
            t = self.tokens[i]
            if t.type in (
                TokenType.OPERATOR_EQUAL,
                TokenType.SEPARATOR_COLON,
                TokenType.SEPARATOR_SEMICOLON,
            ):
                return False
            if t.type in (TokenType.ERROR, TokenType.SIGN):
                return True
            i += 1
        return False

    def _type_real_expected_message(self, ct: Token) -> str:
        """Без «(найдено …)», если дальше ломает слово real мусор, а не буквенная опечатка."""
        if ct.type != TokenType.IDENTIFIER:
            return "Ожидался тип данных real"
        v = ct.value.lower()
        if (
            "real".startswith(v)
            and v != "real"
            and self._lookahead_has_error_or_sign_before_equal_or_colon(self.index)
        ):
            return "Ожидался тип данных real"
        return f"Ожидался тип данных real (найдено «{ct.value}»)"

    def _colon_before_assignment_equal_from(self, from_idx: int) -> bool:
        """Есть ли ':' до первого '=' присваивания (продолжение имени p@i: …)."""
        i = from_idx
        n = len(self.tokens)
        while i < n:
            t = self.tokens[i]
            if t.type == TokenType.SEPARATOR_COLON:
                return True
            if t.type == TokenType.OPERATOR_EQUAL and t.value == "=":
                return False
            i += 1
        return False

    def _scan_broken_real_strict(
        self, from_idx: int
    ) -> Optional[Tuple[int, List[Tuple[int, int]]]]:
        """С позиции from_idx начинается IDENTIFIER — префикс оставшегося «real»; ERROR/SIGN только между кусками."""
        if from_idx >= len(self.tokens) or self.tokens[from_idx].type != TokenType.IDENTIFIER:
            return None
        idx = from_idx
        pos = 0
        target = "real"
        junk: List[Tuple[int, int]] = []
        v = self.tokens[idx].value.lower()
        rem = target[pos:]
        if not rem.startswith(v) or len(v) > len(rem):
            return None
        pos += len(v)
        idx += 1
        while idx < len(self.tokens) and pos < len(target):
            while idx < len(self.tokens) and self.tokens[idx].type in (TokenType.ERROR, TokenType.SIGN):
                t = self.tokens[idx]
                junk.append((t.line, t.start_pos))
                idx += 1
            if idx >= len(self.tokens):
                break
            if self.tokens[idx].type != TokenType.IDENTIFIER:
                return None
            v = self.tokens[idx].value.lower()
            rem = target[pos:]
            if not rem.startswith(v) or len(v) > len(rem):
                return None
            pos += len(v)
            idx += 1
        if pos != len(target):
            return None
        return idx, junk

    def _consume_broken_real_spelling_at_colon_gap(self) -> bool:
        """Между именем и ':' нет — «rea@l», «rea!!l»: части real с ERROR/SIGN между идентификаторами.

        Первый токен — идентификатор, совпадающий с началом real (не поглощаем мусор *перед* ним).
        """
        r = self._scan_broken_real_strict(self.index)
        if r is None:
            return False
        end_idx, junk = r
        for p in junk:
            self._absorbed_real_junk_positions.add(p)
        self.index = end_idx
        return True

    def _attempt_forward_broken_real_recovery(self) -> bool:
        """Ищет склейку «real» начиная с любой позиции ≥ index (после p@i и т.п.)."""
        for j in range(self.index, len(self.tokens)):
            r = self._scan_broken_real_strict(j)
            if r is None:
                continue
            end_idx, junk = r
            for p in junk:
                self._absorbed_real_junk_positions.add(p)
            self.index = end_idx
            self.add_error(self.tokens[j], "Ожидался тип данных real")
            return True
        return False

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
            # «st»/«t» после «con»+ERROR — хвост опечатанного «const», не имя перед ':'
            if (
                self.tokens[i].value.lower() in ("st", "t")
                and i >= 2
                and self.tokens[i - 2].type == TokenType.IDENTIFIER
                and self.tokens[i - 2].value.lower() == "con"
                and self.tokens[i - 1].type == TokenType.ERROR
            ):
                continue
            # «nst» после «co»+ERROR — вторая часть const, не имя перед ':'
            if (
                self.tokens[i].value.lower() == "nst"
                and i >= 2
                and self.tokens[i - 2].type == TokenType.IDENTIFIER
                and self.tokens[i - 2].value.lower() == "co"
                and self.tokens[i - 1].type == TokenType.ERROR
            ):
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
            """Только хвост con@st → «st»/«t», co!…nst, не буква имени после @ (например i в p@i)."""
            if ident_idx == 0:
                return False
            if self.tokens[ident_idx - 1].type != TokenType.ERROR:
                return False
            ident = self.tokens[ident_idx]
            if ident.type != TokenType.IDENTIFIER:
                return False
            low = ident.value.lower()
            if low == "nst":
                return (
                    ident_idx >= 2
                    and self.tokens[ident_idx - 2].type == TokenType.IDENTIFIER
                    and self.tokens[ident_idx - 2].value.lower() == "co"
                )
            if low not in ("st", "t"):
                return False
            for j in range(0, ident_idx - 1):
                if self.tokens[j].type == TokenType.IDENTIFIER:
                    return True
            return False

        good = [i for i in pairs if not is_junk_suffix(i)]
        if good:
            name_i = good[-1]
            if name_i > 0 and self.tokens[name_i - 1].type == TokenType.NUMBER:
                # «3pi» → NUMBER «3» + IDENTIFIER «pi» перед ':' — начало имени с цифры.
                self.index = name_i - 1
            else:
                self.index = name_i
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
        parsed_const_keyword = self.match(TokenType.KEYWORD_CONST, "const")
        broken_const_recovered = False
        if not parsed_const_keyword:
            inside, trailing, resume_idx, spelled, closed_by_keyword_const = (
                self._split_broken_const_spelling()
            )
            err_chunks = self._collect_error_chunks_near_start()

            if spelled:
                broken_const_recovered = True
                if closed_by_keyword_const and inside:
                    for i in range(resume_idx - 1):
                        t0 = self.tokens[i]
                        self.add_error(t0, self._invalid_symbol_message_simple(t0.value))
                        has_error = True
                    for te in trailing:
                        self.add_error(te, self._invalid_symbol_message_simple(te.value))
                        has_error = True
                    self.index = resume_idx
                else:
                    head = self.tokens[0]
                    if inside:
                        sym = self._format_invalid_symbols_in_const_prefix(inside)
                        self.add_error(
                            head,
                            f"Ожидалось ключевое слово const ({sym})",
                            fragment_override="const",
                        )
                        has_error = True
                    else:
                        self.add_error(
                            head,
                            "Ожидалось ключевое слово const",
                            fragment_override="const",
                        )
                        has_error = True
                    for te in trailing:
                        self.add_error(te, self._invalid_symbol_message_simple(te.value))
                        has_error = True
                    self.index = resume_idx
            elif inside:
                sym = self._format_invalid_symbols_in_const_prefix(inside)
                head = self.tokens[0]
                self.add_error(
                    head,
                    f"Ожидалось ключевое слово const ({sym})",
                    fragment_override="const",
                )
                has_error = True
                broken_const_recovered = True
                self.index = resume_idx
            elif err_chunks:
                sym = self._format_invalid_symbols_in_const_prefix(err_chunks)
                head = self.tokens[0]
                self.add_error(
                    head,
                    f"Ожидалось ключевое слово const ({sym})",
                    fragment_override="const",
                )
                has_error = True
                broken_const_recovered = True
                self._jump_after_invalid_const()
            else:
                self.add_error(self.current(), "Ожидалось ключевое слово const")
            has_error = True

            token = self.current()

        const_decl_context = parsed_const_keyword or broken_const_recovered

        extra_const_count = 0
        while self.current() and self.current().type == TokenType.KEYWORD_CONST:
            if self.current().value == "const":
                extra_const_count += 1
            self.next()
        if extra_const_count > 0:
            self.add_error(self.current(), "Лишнее ключевое слово 'const' перед идентификатором")
            has_error = True

        cur0 = self.current()
        if (
            cur0
            and cur0.type == TokenType.SEPARATOR_SEMICOLON
            and self.index > 0
            and self.tokens[self.index - 1].type == TokenType.KEYWORD_CONST
        ):
            self.add_error(cur0, self._invalid_symbol_message_simple(";"))
            return False, self.errors

        if not self.match(TokenType.IDENTIFIER):
            tok = self.current()
            digit_start_recovered = False
            if tok and tok.type == TokenType.NUMBER and const_decl_context:
                self.add_error(
                    tok,
                    f"Ожидался идентификатор имени константы; лексема «{tok.value}» "
                    "недопустима — имя не может начинаться с цифры",
                )
                has_error = True
                self._recover_after_digit_start_constant_name()
                digit_start_recovered = True
            elif tok and tok.type == TokenType.ERROR:
                if (
                    self.index > 0
                    and self.tokens[self.index - 1].type == TokenType.KEYWORD_CONST
                ):
                    self.add_error(
                        tok,
                        self._invalid_symbol_message_simple(tok.value),
                    )
                has_error = True
            elif (
                tok
                and tok.type == TokenType.SIGN
                and self.index > 0
                and self.tokens[self.index - 1].type == TokenType.KEYWORD_CONST
            ):
                self.add_error(tok, self._invalid_symbol_message_simple(tok.value))
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
            if not digit_start_recovered:
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
                if (
                    const_decl_context
                    and self.current()
                    and self.current().type == TokenType.NUMBER
                ):
                    tokn = self.current()
                    self.add_error(
                        tokn,
                        f"Ожидался идентификатор имени константы; лексема «{tokn.value}» "
                        "недопустима — имя не может начинаться с цифры",
                    )
                    has_error = True
                    self._recover_after_digit_start_constant_name()
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
            broken_real_stitched = False
            if ct and ct.type == TokenType.IDENTIFIER:
                br_first_idx = self.index
                if self._consume_broken_real_spelling_at_colon_gap():
                    self.add_error(self.tokens[br_first_idx], "Ожидался тип данных real")
                    has_error = True
                    broken_real_stitched = True
                    self._suppress_next_real_expected_msg = True
                    self._skip_duplicate_real_msg = True
                    colon_count, colon_start = self._consume_repeats(TokenType.SEPARATOR_COLON)
                    ct = self.current()

            if colon_count == 0:
                if not broken_real_stitched:
                    ct = self.current()
                    if ct and ct.type == TokenType.KEYWORD_REAL:
                        self.add_error(
                            ct,
                            "Пропущено ':' между именем константы и типом данных real",
                        )
                    elif ct and ct.type == TokenType.IDENTIFIER:
                        prev_tok = self.tokens[self.index - 1] if self.index > 0 else None
                        if (
                            prev_tok
                            and prev_tok.type == TokenType.IDENTIFIER
                            and not self._after_digit_split_name_recovery
                        ):
                            self.add_error(prev_tok, "Пропущено ':' после идентификатора")
                            self.add_error(ct, self._type_real_expected_message(ct))
                        else:
                            if self._after_digit_split_name_recovery:
                                self._after_digit_split_name_recovery = False
                            self.add_error(ct, self._type_real_expected_message(ct))
                        self._skip_duplicate_real_msg = True
                    elif (
                        ct
                        and ct.type == TokenType.SEPARATOR_SEMICOLON
                        and const_decl_context
                        and self.index > 0
                        and self.tokens[self.index - 1].type == TokenType.IDENTIFIER
                    ):
                        prev_name = self.tokens[self.index - 1]
                        self.add_error(ct, self._invalid_symbol_message_simple(ct.value))
                        self.add_error(prev_name, "Пропущено ':' после идентификатора")
                        return False, self.errors
                    elif ct and ct.type == TokenType.ERROR:
                        prev_tok = self.tokens[self.index - 1] if self.index > 0 else None
                        self.add_error(ct, self._invalid_symbol_message_simple(ct.value))
                        if prev_tok and prev_tok.type == TokenType.IDENTIFIER:
                            if not self._colon_before_assignment_equal_from(self.index):
                                self.add_error(
                                    prev_tok, "Пропущено ':' после идентификатора"
                                )
                    else:
                        self.add_error(ct, "Отсутствует ':'")
                    has_error = True
                if not broken_real_stitched and self._attempt_forward_broken_real_recovery():
                    broken_real_stitched = True
                    self._suppress_next_real_expected_msg = True
                    self._skip_duplicate_real_msg = True
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

        br_after_colon_stitched = False
        if self.current() and self.current().type == TokenType.IDENTIFIER:
            br_after_colon = self.index
            if self._consume_broken_real_spelling_at_colon_gap():
                self.add_error(self.tokens[br_after_colon], "Ожидался тип данных real")
                br_after_colon_stitched = True
        if not br_after_colon_stitched and self._attempt_forward_broken_real_recovery():
            br_after_colon_stitched = True
        if br_after_colon_stitched:
            has_error = True
            self._suppress_next_real_expected_msg = True
            self._skip_duplicate_real_msg = True

        if not self.match(TokenType.KEYWORD_REAL, 'real'):
            rt = self.current()
            if self._suppress_next_real_expected_msg:
                self._suppress_next_real_expected_msg = False
                self._skip_duplicate_real_msg = False
                has_error = True
            elif (
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

    def absorbed_real_junk_positions(self):
        """Позиции (строка, позиция) ERROR/SIGN, поглощённые при склейке «real» — не дублировать как лексические."""
        return frozenset(self._absorbed_real_junk_positions)


ParserV2 = Parser


if __name__ == "__main__":
    import sys

    print(
        "parser.py — это модуль парсера (его импортирует main.py), а не точка входа приложения.\n"
        "Чтобы запустить окно редактора, выполните из папки text_editor:\n"
        "  python main.py\n"
        "или из корня проекта Complier:\n"
        "  python text_editor/main.py",
        file=sys.stderr,
    )
    raise SystemExit(2)