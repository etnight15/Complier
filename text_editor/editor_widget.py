import re

from PyQt6.QtWidgets import QTextEdit, QWidget, QPlainTextEdit
from PyQt6.QtGui import (
    QFont,
    QKeyEvent,
    QTextCursor,
    QPainter,
    QColor,
    QTextFormat,
    QTextCharFormat,
    QSyntaxHighlighter,
)
from PyQt6.QtCore import Qt, QRect, QSize


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


class PascalSyntaxHighlighter(QSyntaxHighlighter):
    """Базовая подсветка Pascal-подобного синтаксиса для редактора."""

    def __init__(self, document, font_size: int = 11):
        super().__init__(document)
        self._font_size = font_size
        self._build_rules()

    def _fmt(self, color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
        fmt.setFontItalic(italic)
        return fmt

    def _build_rules(self):
        keyword_fmt = self._fmt("#0000CC", bold=True)
        number_fmt = self._fmt("#098658")
        operator_fmt = self._fmt("#795E26")
        string_fmt = self._fmt("#A31515")
        comment_fmt = self._fmt("#008000", italic=True)

        keywords = [
            "const", "real", "integer", "boolean", "char", "string",
            "var", "begin", "end", "if", "then", "else", "while", "do",
            "procedure", "function", "program", "uses", "type", "of",
            "div", "mod", "and", "or", "not", "true", "false",
        ]
        self._rules: list[tuple[re.Pattern[str], QTextCharFormat]] = [
            (re.compile(r"\b(" + "|".join(keywords) + r")\b", re.IGNORECASE), keyword_fmt),
            (re.compile(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), number_fmt),
            (re.compile(r"'(?:[^'\\]|\\.)*'"), string_fmt),
            (re.compile(r"//[^\n]*"), comment_fmt),
            (re.compile(r"\{[^}]*\}"), comment_fmt),
            (re.compile(r":=|[+\-*/=():;.]"), operator_fmt),
        ]

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._font_size = 11
        self.highlighter = None
        self.setup_editor()

    def setup_editor(self):
        self.set_font_size(self._font_size)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("Введите текст программы на Pascal...")

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.highlighter = PascalSyntaxHighlighter(self.document(), self._font_size)

        self.update_line_number_area_width()
        self.highlight_current_line()

    def set_font_size(self, size: int):
        self._font_size = max(6, min(48, size))
        font = QFont("Courier New", self._font_size)
        font.setFixedPitch(True)
        self.setFont(font)
        self.document().setDefaultFont(font)
        self._apply_font_to_entire_document(font)
        if self.highlighter:
            self.highlighter.rehighlight()
        self.update_line_number_area_width()

    def _apply_font_to_entire_document(self, font: QFont):
        """Сбросить размер у всего текста (иначе уменьшение не видно после подсветки)."""
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFont(font)
        cursor.setCharFormat(fmt)
        cursor.clearSelection()
        cursor.endEditBlock()

    def get_font_size(self) -> int:
        return self._font_size

    def set_placeholder(self, text: str):
        self.setPlaceholderText(text)

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(120, 120, 120))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(230, 240, 255)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
        else:
            super().keyPressEvent(event)

    def get_current_line(self):
        cursor = self.textCursor()
        return cursor.blockNumber() + 1

    def get_current_column(self):
        cursor = self.textCursor()
        return cursor.columnNumber() + 1

    def get_text_length(self):
        return len(self.toPlainText())

    def insert_text_at_cursor(self, text):
        self.insertPlainText(text)

    def get_selected_text(self):
        cursor = self.textCursor()
        return cursor.selectedText() if cursor.hasSelection() else ""

    def set_error_position(self, line, column):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for _ in range(line - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Down)

        for _ in range(column - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Right)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def highlight_error(self, line, start_pos, end_pos):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for _ in range(line - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Down)

        for _ in range(start_pos - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Right)

        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            end_pos - start_pos + 1,
        )

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 200, 200))
        fmt.setForeground(QColor(255, 0, 0))

        cursor.mergeCharFormat(fmt)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def highlight_search_result(self, line, start_pos, end_pos):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for _ in range(line - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Down)

        for _ in range(start_pos - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Right)

        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            end_pos - start_pos + 1,
        )

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 0))
        fmt.setForeground(QColor(0, 0, 0))

        cursor.mergeCharFormat(fmt)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_highlighting(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 255))
        fmt.setForeground(QColor(0, 0, 0))

        cursor.mergeCharFormat(fmt)
        cursor.clearSelection()
        if self.highlighter:
            self.highlighter.rehighlight()
