"""Простая интернационализация интерфейса (ru / en)."""

from __future__ import annotations

from typing import Dict


_STRINGS: Dict[str, Dict[str, str]] = {
  "ru": {
    "app_title": "Compiler",
    "status_ready": "Готов к работе",
    "status_line_col_chars": "Строка: {line}, Колонка: {col} | Символов: {chars}",
    "status_new_file": "Создан новый файл",
    "status_opened": "Открыт файл: {path}",
    "status_saved": "Файл сохранен: {name}",
    "status_analysis_errors": "Анализ завершен. Всего ошибок: {count}",
    "status_analysis_lex": "Анализ завершен. Лексических ошибок: {count}",
    "status_analysis_ok": "Анализ завершен. Всего ошибок: 0",
    "status_analysis_fail": "Ошибка при анализе",
    "menu_file": "Файл",
    "menu_edit": "Правка",
    "menu_view": "Вид",
    "menu_text": "Текст",
    "menu_run": "Пуск",
    "menu_help": "Справка",
    "action_new": "Создать",
    "action_open": "Открыть",
    "action_save": "Сохранить",
    "action_save_as": "Сохранить как",
    "action_exit": "Выход",
    "action_undo": "Отмена",
    "action_redo": "Повтор",
    "action_cut": "Вырезать",
    "action_copy": "Копировать",
    "action_paste": "Вставить",
    "action_delete": "Удалить",
    "action_select_all": "Выделить все",
    "action_close_tab": "Закрыть вкладку",
    "action_new_tab": "Новая вкладка",
    "action_find": "Найти",
    "action_run": "Запустить анализатор",
    "action_expr": "Анализ арифметического выражения",
    "action_help": "Вызов справки",
    "action_shortcuts": "Горячие клавиши",
    "action_about": "О программе",
    "action_font_increase": "Увеличить шрифт",
    "action_font_decrease": "Уменьшить шрифт",
    "action_font_reset": "Сбросить размер шрифта",
    "font_size_status": "Размер шрифта",
    "menu_language": "Язык интерфейса",
    "lang_ru": "Русский",
    "lang_en": "English",
    "tab_new_file": "Новый файл",
    "tab_results": "Результаты",
    "tab_tokens": "Таблица лексем",
    "tab_syntax_errors": "Синтаксические ошибки",
    "tab_search_results": "Результаты поиска",
    "tab_semantics_ast": "Семантика и AST",
    "tab_tetrads_poliz": "Тетрады и ПОЛИЗ",
    "tab_ir_opt": "IR и оптимизация",
    "search_find": "Найти:",
    "search_placeholder": "Введите текст или регулярное выражение...",
    "search_regex_presets": "Шаблоны RegExp:",
    "search_regex_choose": "— выбрать шаблон —",
    "search_type": "Тип поиска:",
    "search_type_plain": "Обычный поиск",
    "search_type_regex": "Регулярное выражение",
    "search_type_word": "Целое слово",
    "search_button": "Найти",
    "search_count": "Найдено: {count}",
    "search_no_editor": "Нет данных для поиска. Введите текст в редактор.",
    "search_no_pattern": "Введите текст для поиска",
    "search_no_regex": "Введите регулярное выражение",
    "search_no_matches": "Совпадений не найдено для: {pattern}",
    "search_done": "Поиск завершен. Найдено совпадений: {count}",
    "search_results_title": "Результаты поиска",
    "search_regex_error": "Неверное регулярное выражение: {err}",
    "search_error": "Ошибка при поиске: {err}",
    "editor_placeholder": "Введите текст программы на Pascal...",
    "output_placeholder": "Результаты работы языкового процессора...",
    "ast_placeholder": "Дерево AST появится после успешного синтаксического анализа…",
    "ir_placeholder": "Трёхадресный код и результаты локальных оптимизаций появятся после анализа (F5)…",
    "poliz_placeholder": "ПОЛИЗ и результат вычисления появятся для выражений из целых чисел…",
    "col_code": "Код",
    "col_type": "Тип",
    "col_lexeme": "Лексема",
    "col_location": "Местоположение",
    "col_fragment": "Неверный фрагмент",
    "col_error_desc": "Описание ошибки",
    "col_match": "Найденная подстрока",
    "col_length": "Длина",
    "col_sem_desc": "Описание",
    "col_op": "op",
    "col_arg1": "arg1",
    "col_arg2": "arg2",
    "col_result": "result",
    "msg_cannot_close_last": "Нельзя закрыть последнюю вкладку",
    "msg_save_title": "Сохранение",
    "msg_save_prompt": "Файл '{name}' был изменен. Сохранить изменения?",
    "msg_error": "Ошибка",
    "msg_open_failed": "Не удалось открыть файл: {err}",
    "msg_save_failed": "Не удалось сохранить файл: {err}",
    "msg_info": "Информация",
    "msg_enter_text": "Введите текст для анализа",
    "msg_enter_expr": "Введите арифметическое выражение для анализа",
    "dialog_open": "Открыть файл",
    "dialog_save_as": "Сохранить файл как",
    "filter_text": "Текстовые файлы (*.txt);;Все файлы (*.*)",
    "drop_opened": "Открыт перетаскиванием: {name}",
    "shortcuts_title": "Горячие клавиши",
    "shortcuts_body": (
      "Файл:\n"
      "  Ctrl+N — новый файл\n"
      "  Ctrl+O — открыть\n"
      "  Ctrl+S — сохранить\n"
      "  Ctrl+Shift+S — сохранить как\n"
      "  Ctrl+W — закрыть вкладку\n"
      "  Ctrl+Q — выход\n\n"
      "Правка:\n"
      "  Ctrl+Z / Ctrl+Y — отмена / повтор\n"
      "  Ctrl+X / Ctrl+C / Ctrl+V — вырезать / копировать / вставить\n"
      "  Ctrl+A — выделить всё\n"
      "  Del — удалить\n\n"
      "Вид:\n"
      "  Ctrl++ / Ctrl+- — размер шрифта\n"
      "  Ctrl+0 — сброс шрифта\n\n"
      "Поиск:\n"
      "  Ctrl+F — фокус на поле поиска\n"
      "  F3 — найти\n\n"
      "Анализ:\n"
      "  F5 — анализ const/real\n"
      "  F6 — арифметическое выражение\n"
      "  F1 — справка"
    ),
    "task_action": "Постановка задачи",
    "grammar_action": "Грамматика",
    "classification_action": "Классификация грамматики",
    "method_action": "Метод анализа",
    "example_action": "Тестовый пример",
    "references_action": "Список литературы",
    "source_action": "Исходный код программы",
    "coursework_action": "Курсовая работа",
    "toolbar_new": "Новый",
    "toolbar_open": "Открыть",
    "toolbar_save": "Сохранить",
    "toolbar_run": "Пуск",
    "toolbar_expr": "Выражение",
    "toolbar_help": "Справка",
  },
  "en": {
    "app_title": "Compiler",
    "status_ready": "Ready",
    "status_line_col_chars": "Line: {line}, Col: {col} | Chars: {chars}",
    "status_new_file": "New file created",
    "status_opened": "Opened: {path}",
    "status_saved": "Saved: {name}",
    "status_analysis_errors": "Analysis done. Errors: {count}",
    "status_analysis_lex": "Analysis done. Lexical errors: {count}",
    "status_analysis_ok": "Analysis done. Errors: 0",
    "status_analysis_fail": "Analysis error",
    "menu_file": "File",
    "menu_edit": "Edit",
    "menu_view": "View",
    "menu_text": "Text",
    "menu_run": "Run",
    "menu_help": "Help",
    "action_new": "New",
    "action_open": "Open",
    "action_save": "Save",
    "action_save_as": "Save As",
    "action_exit": "Exit",
    "action_undo": "Undo",
    "action_redo": "Redo",
    "action_cut": "Cut",
    "action_copy": "Copy",
    "action_paste": "Paste",
    "action_delete": "Delete",
    "action_select_all": "Select All",
    "action_close_tab": "Close Tab",
    "action_new_tab": "New Tab",
    "action_find": "Find",
    "action_run": "Run Analyzer",
    "action_expr": "Arithmetic Expression Analysis",
    "action_help": "Help",
    "action_shortcuts": "Keyboard Shortcuts",
    "action_about": "About",
    "action_font_increase": "Increase Font Size",
    "action_font_decrease": "Decrease Font Size",
    "action_font_reset": "Reset Font Size",
    "font_size_status": "Font size",
    "menu_language": "Interface Language",
    "lang_ru": "Русский",
    "lang_en": "English",
    "tab_new_file": "New file",
    "tab_results": "Results",
    "tab_tokens": "Token Table",
    "tab_syntax_errors": "Syntax Errors",
    "tab_search_results": "Search Results",
    "tab_semantics_ast": "Semantics and AST",
    "tab_tetrads_poliz": "Quads and RPN",
    "tab_ir_opt": "IR and Optimization",
    "search_find": "Find:",
    "search_placeholder": "Enter text or regular expression...",
    "search_regex_presets": "RegExp presets:",
    "search_regex_choose": "— choose preset —",
    "search_type": "Search type:",
    "search_type_plain": "Plain search",
    "search_type_regex": "Regular expression",
    "search_type_word": "Whole word",
    "search_button": "Find",
    "search_count": "Found: {count}",
    "search_no_editor": "Nothing to search. Enter text in the editor.",
    "search_no_pattern": "Enter search text",
    "search_no_regex": "Enter a regular expression",
    "search_no_matches": "No matches for: {pattern}",
    "search_done": "Search done. Matches: {count}",
    "search_results_title": "Search results",
    "search_regex_error": "Invalid regular expression: {err}",
    "search_error": "Search error: {err}",
    "editor_placeholder": "Enter Pascal program text...",
    "output_placeholder": "Language processor output...",
    "ast_placeholder": "AST tree appears after successful syntax analysis…",
    "ir_placeholder": "Three-address code appears after analysis (F5)…",
    "poliz_placeholder": "RPN and evaluation appear for integer expressions…",
    "col_code": "Code",
    "col_type": "Type",
    "col_lexeme": "Lexeme",
    "col_location": "Location",
    "col_fragment": "Invalid fragment",
    "col_error_desc": "Error description",
    "col_match": "Match",
    "col_length": "Length",
    "col_sem_desc": "Description",
    "col_op": "op",
    "col_arg1": "arg1",
    "col_arg2": "arg2",
    "col_result": "result",
    "msg_cannot_close_last": "Cannot close the last tab",
    "msg_save_title": "Save",
    "msg_save_prompt": "File '{name}' has been modified. Save changes?",
    "msg_error": "Error",
    "msg_open_failed": "Could not open file: {err}",
    "msg_save_failed": "Could not save file: {err}",
    "msg_info": "Information",
    "msg_enter_text": "Enter text to analyze",
    "msg_enter_expr": "Enter an arithmetic expression to analyze",
    "dialog_open": "Open File",
    "dialog_save_as": "Save File As",
    "filter_text": "Text files (*.txt);;All files (*.*)",
    "drop_opened": "Opened via drag-and-drop: {name}",
    "shortcuts_title": "Keyboard Shortcuts",
    "shortcuts_body": (
      "File:\n"
      "  Ctrl+N — new file\n"
      "  Ctrl+O — open\n"
      "  Ctrl+S — save\n"
      "  Ctrl+Shift+S — save as\n"
      "  Ctrl+W — close tab\n"
      "  Ctrl+Q — quit\n\n"
      "Edit:\n"
      "  Ctrl+Z / Ctrl+Y — undo / redo\n"
      "  Ctrl+X / Ctrl+C / Ctrl+V — cut / copy / paste\n"
      "  Ctrl+A — select all\n"
      "  Del — delete\n\n"
      "View:\n"
      "  Ctrl++ / Ctrl+- — font size\n"
      "  Ctrl+0 — reset font\n\n"
      "Search:\n"
      "  Ctrl+F — focus search field\n"
      "  F3 — find\n\n"
      "Analysis:\n"
      "  F5 — const/real analysis\n"
      "  F6 — expression analysis\n"
      "  F1 — help"
    ),
    "task_action": "Problem statement",
    "grammar_action": "Grammar",
    "classification_action": "Grammar classification",
    "method_action": "Analysis method",
    "example_action": "Test example",
    "references_action": "References",
    "source_action": "Program source",
    "coursework_action": "Coursework",
    "toolbar_new": "New",
    "toolbar_open": "Open",
    "toolbar_save": "Save",
    "toolbar_run": "Run",
    "toolbar_expr": "Expr",
    "toolbar_help": "Help",
  },
}


class I18n:
    def __init__(self, language: str = "ru"):
        self._language = language if language in _STRINGS else "ru"

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language in _STRINGS:
            self._language = language

    def tr(self, key: str, **kwargs) -> str:
        text = _STRINGS.get(self._language, _STRINGS["ru"]).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text

    def available_languages(self) -> list[str]:
        return list(_STRINGS.keys())
