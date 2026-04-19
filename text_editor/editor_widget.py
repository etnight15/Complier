from PyQt6.QtWidgets import QTextEdit, QWidget, QPlainTextEdit
from PyQt6.QtGui import QFont, QKeyEvent, QTextCursor, QPainter, QColor, QTextFormat, QTextCharFormat
from PyQt6.QtCore import Qt, QRect, QSize


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_editor()
        
    def setup_editor(self):
        font = QFont("Courier New", 11)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("Введите текст программы на Pascal...")
        
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        self.update_line_number_area_width()
        self.highlight_current_line()
        
    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

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
                painter.drawText(0, top, self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            
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
        
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, end_pos - start_pos + 1)
        
        format = QTextCharFormat()
        format.setBackground(QColor(255, 200, 200))
        format.setForeground(QColor(255, 0, 0))
        
        cursor.mergeCharFormat(format)
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def highlight_search_result(self, line, start_pos, end_pos):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        for _ in range(line - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
        
        for _ in range(start_pos - 1):
            cursor.movePosition(QTextCursor.MoveOperation.Right)
        
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, end_pos - start_pos + 1)
        
        format = QTextCharFormat()
        format.setBackground(QColor(255, 255, 0))
        format.setForeground(QColor(0, 0, 0))
        
        cursor.mergeCharFormat(format)
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def clear_highlighting(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        
        format = QTextCharFormat()
        format.setBackground(QColor(255, 255, 255))
        format.setForeground(QColor(0, 0, 0))
        
        cursor.mergeCharFormat(format)
        cursor.clearSelection()


class SyntaxHighlighter:
    def __init__(self, parent=None):
        self.parent = parent
        self.highlighting_rules = []
        
    def highlight_block(self, text):
        pass
        
    def add_rule(self, pattern, format):
        self.highlighting_rules.append((pattern, format))