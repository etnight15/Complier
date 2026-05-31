import sys
import os
import re
from functools import partial
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QTextEdit, QToolBar, QMenu, QFileDialog, QMessageBox, 
                             QSplitter, QStatusBar, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget, QComboBox,
                             QPushButton, QHBoxLayout, QLineEdit, QDialog,
                             QDialogButtonBox, QTextBrowser)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl, QKeyCombination, QEvent
from PyQt6.QtGui import (
    QAction, QKeySequence, QTextCursor, QFont, QIcon, QPixmap, QPainter, QColor,
    QBrush, QTextCharFormat, QDragEnterEvent, QDropEvent, QKeyEvent,
)
from editor_widget import CodeEditor
from i18n import I18n
from scanner import Scanner, Token, TokenType
from parser import Parser, SyntaxError
from expr_scanner import ExprScanner, ExprToken
from expr_parser import ExprParser, ExprSyntaxError
from ir_codegen import IrGenerator, format_ir
from ir_optimize import apply_optimizations, apply_quad_optimizations, format_quads
 

def _course_assets_base_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "text_editor", "assets")
        if os.path.isdir(bundled):
            return bundled
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class EditorTab(QWidget):
    textChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.text_changed = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = CodeEditor()
        self.editor.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.editor)
        
    def on_text_changed(self):
        self.text_changed = True
        self.textChanged.emit()
        
    def get_text(self):
        return self.editor.toPlainText()
        
    def set_text(self, text):
        self.editor.setPlainText(text)
        self.text_changed = False
        
    def clear(self):
        self.editor.clear()
        self.current_file = None
        self.text_changed = False
        
    def has_changes(self):
        return self.text_changed
        
    def get_current_line(self):
        return self.editor.get_current_line()
        
    def get_current_column(self):
        return self.editor.get_current_column()
        
    def go_to_position(self, line, pos):
        self.editor.set_error_position(line, pos)
    
    def highlight_search_result(self, line, start_pos, end_pos):
        self.editor.highlight_search_result(line, start_pos, end_pos)
    
    def clear_highlighting(self):
        self.editor.clear_highlighting()
    
    def highlight_error(self, line, start_pos, end_pos):
        self.editor.highlight_error(line, start_pos, end_pos)
        
    def undo(self):
        self.editor.undo()
        
    def redo(self):
        self.editor.redo()
        
    def cut(self):
        self.editor.cut()
        
    def copy(self):
        self.editor.copy()
        
    def paste(self):
        self.editor.paste()
        
    def select_all(self):
        self.editor.selectAll()

    def set_font_size(self, size: int):
        self.editor.set_font_size(size)

    def set_editor_placeholder(self, text: str):
        self.editor.set_placeholder(text)


class TokenTable(QTableWidget):
    tokenClicked = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
        
    def set_header_labels(self, labels):
        self.setHorizontalHeaderLabels(labels)

    def setup_table(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Код", "Тип", "Лексема", "Местоположение"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.itemClicked.connect(self.on_item_clicked)
        
    def on_item_clicked(self, item):
        row = item.row()
        location_item = self.item(row, 3)
        if location_item and location_item.toolTip():
            try:
                line, pos = map(int, location_item.toolTip().split(','))
                self.tokenClicked.emit(line, pos)
            except:
                pass
        
    def clear_table(self):
        self.setRowCount(0)
        
    def add_token(self, token):
        row = self.rowCount()
        self.insertRow(row)
        
        code_item = QTableWidgetItem(str(token.get_type_code()))
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        code_item.setForeground(QBrush(QColor(0, 0, 0)))
        self.setItem(row, 0, code_item)
        
        type_item = QTableWidgetItem(token.get_type_name())
        type_item.setForeground(QBrush(QColor(0, 0, 0)))
        self.setItem(row, 1, type_item)
        
        lexeme_item = QTableWidgetItem(token.value)
        lexeme_item.setForeground(QBrush(QColor(0, 0, 0)))
        if token.value.isspace():
            lexeme_item.setText("␣" * len(token.value))
            lexeme_item.setForeground(QBrush(QColor(150, 150, 150)))
        self.setItem(row, 2, lexeme_item)
        
        location_text = f"стр.{token.line}, поз.{token.start_pos}-{token.end_pos}"
        location_item = QTableWidgetItem(location_text)
        location_item.setForeground(QBrush(QColor(0, 0, 0)))
        location_item.setToolTip(f"{token.line},{token.start_pos}")
        self.setItem(row, 3, location_item)
        
        if token.type == TokenType.ERROR:
            pink_bg = QBrush(QColor(255, 200, 200))
            red_color = QBrush(QColor(255, 0, 0))
            for col in range(4):
                item = self.item(row, col)
                item.setBackground(pink_bg)
                item.setForeground(red_color)


class SyntaxErrorTable(QTableWidget):
    errorClicked = pyqtSignal(int, int, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def set_header_labels(self, labels):
        self.setHorizontalHeaderLabels(labels)
        
    def setup_table(self):
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Неверный фрагмент", "Местоположение", "Описание ошибки"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.itemClicked.connect(self.on_item_clicked)
        
    def on_item_clicked(self, item):
        row = item.row()
        location_item = self.item(row, 1)
        if location_item and location_item.toolTip():
            try:
                line, start_pos, end_pos = map(int, location_item.toolTip().split(','))
                self.errorClicked.emit(line, start_pos, end_pos, row)
            except:
                pass
        
    def clear_table(self):
        self.setRowCount(0)
        
    def add_error(self, fragment: str, line: int, start_pos: int, end_pos: int, message: str):
        row = self.rowCount()
        self.insertRow(row)
        
        frag_item = QTableWidgetItem(fragment)
        frag_item.setBackground(QBrush(QColor(255, 200, 200)))
        frag_item.setForeground(QBrush(QColor(255, 0, 0)))
        self.setItem(row, 0, frag_item)
        
        loc_text = f"строка {line}, позиция {start_pos}"
        loc_item = QTableWidgetItem(loc_text)
        loc_item.setBackground(QBrush(QColor(255, 200, 200)))
        loc_item.setForeground(QBrush(QColor(255, 0, 0)))
        loc_item.setToolTip(f"{line},{start_pos},{end_pos}")
        self.setItem(row, 1, loc_item)
        
        msg_item = QTableWidgetItem(message)
        msg_item.setBackground(QBrush(QColor(255, 200, 200)))
        msg_item.setForeground(QBrush(QColor(255, 0, 0)))
        self.setItem(row, 2, msg_item)
        
        return row


class SearchResultTable(QTableWidget):
    resultClicked = pyqtSignal(int, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def set_header_labels(self, labels):
        self.setHorizontalHeaderLabels(labels)
        
    def setup_table(self):
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Найденная подстрока", "Местоположение", "Длина"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.itemClicked.connect(self.on_item_clicked)
        
    def on_item_clicked(self, item):
        row = item.row()
        location_item = self.item(row, 1)
        if location_item and location_item.toolTip():
            try:
                line, start_pos, end_pos = map(int, location_item.toolTip().split(','))
                self.resultClicked.emit(line, start_pos, end_pos)
            except:
                pass
        
    def clear_table(self):
        self.setRowCount(0)
        
    def add_result(self, match_text: str, line: int, start_pos: int, end_pos: int, length: int):
        row = self.rowCount()
        self.insertRow(row)
        
        match_item = QTableWidgetItem(match_text)
        self.setItem(row, 0, match_item)
        
        loc_text = f"строка {line}, позиция {start_pos}"
        loc_item = QTableWidgetItem(loc_text)
        loc_item.setToolTip(f"{line},{start_pos},{end_pos}")
        self.setItem(row, 1, loc_item)
        
        len_item = QTableWidgetItem(str(length))
        len_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 2, len_item)
        
        return row


class SemanticTable(QTableWidget):
    semanticClicked = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def set_header_labels(self, labels):
        self.setHorizontalHeaderLabels(labels)

    def setup_table(self):
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Неверный фрагмент", "Местоположение", "Описание"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.itemClicked.connect(self.on_item_clicked)

    def on_item_clicked(self, item):
        row = item.row()
        location_item = self.item(row, 1)
        if location_item and location_item.toolTip():
            try:
                line, pos = map(int, location_item.toolTip().split(","))
                self.semanticClicked.emit(line, pos)
            except Exception:
                pass

    def clear_table(self):
        self.setRowCount(0)

    def add_result(self, fragment: str, line: int, pos: int, message: str, *, is_error: bool = False):
        row = self.rowCount()
        self.insertRow(row)

        frag_item = QTableWidgetItem(fragment)
        loc_text = f"Строка: {line}, поз. {pos}"
        loc_item = QTableWidgetItem(loc_text)
        loc_item.setToolTip(f"{line},{pos}")
        msg_item = QTableWidgetItem(message)

        if is_error:
            pink_bg = QBrush(QColor(255, 200, 200))
            red_fg = QBrush(QColor(180, 0, 0))
            for cell in (frag_item, loc_item, msg_item):
                cell.setBackground(pink_bg)
                cell.setForeground(red_fg)

        self.setItem(row, 0, frag_item)
        self.setItem(row, 1, loc_item)
        self.setItem(row, 2, msg_item)

        return row


class QuadTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def setup_table(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["op", "arg1", "arg2", "result"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

    def clear_table(self):
        self.setRowCount(0)

    def add_quad(self, quad):
        row = self.rowCount()
        self.insertRow(row)
        for col, value in enumerate((quad.op, quad.arg1, quad.arg2, quad.result)):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, col, item)


class ExprGrammarErrorTable(QTableWidget):
    errorClicked = pyqtSignal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["неверный фрагмент", "местоположение", "Описание"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item):
        row = item.row()
        location_item = self.item(row, 1)
        if location_item and location_item.toolTip():
            try:
                line, start_pos, end_pos = map(int, location_item.toolTip().split(","))
                self.errorClicked.emit(line, start_pos, end_pos, row)
            except Exception:
                pass

    def clear_table(self):
        self.setRowCount(0)

    def show_no_errors(self):
        self.clear_table()
        self.insertRow(0)
        for col, text in enumerate(("—", "—", "Ошибок грамматики выражения нет.")):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(0, col, item)

    def add_error(self, fragment: str, line: int, start_pos: int, end_pos: int, message: str):
        row = self.rowCount()
        self.insertRow(row)
        pink_bg = QBrush(QColor(255, 200, 200))
        red_fg = QBrush(QColor(180, 0, 0))

        frag_item = QTableWidgetItem(fragment)
        loc_text = f"строка {line}, позиция {start_pos}"
        loc_item = QTableWidgetItem(loc_text)
        loc_item.setToolTip(f"{line},{start_pos},{end_pos}")
        msg_item = QTableWidgetItem(message)

        for item in (frag_item, loc_item, msg_item):
            item.setBackground(pink_bg)
            item.setForeground(red_fg)

        self.setItem(row, 0, frag_item)
        self.setItem(row, 1, loc_item)
        self.setItem(row, 2, msg_item)


class IrOptimizationPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "font-weight: 600; padding: 6px 8px; background: #f5f5f5; border-bottom: 1px solid #ddd;"
        )
        layout.addWidget(self.status_label)

        self.ir_output = QTextEdit()
        self.ir_output.setReadOnly(True)
        self.ir_output.setPlaceholderText(
            "Трёхадресный код и результаты локальных оптимизаций появятся после анализа (F5)…"
        )
        layout.addWidget(self.ir_output)

    def clear(self):
        self.status_label.clear()
        self.ir_output.clear()

    def set_status(self, text: str, *, success: bool = True):
        color = "#1e7e34" if success else "#c62828"
        self.status_label.setStyleSheet(
            f"font-weight: 600; padding: 6px 8px; color: {color}; "
            "background: #f5f5f5; border-bottom: 1px solid #ddd;"
        )
        self.status_label.setText(text)

    def set_ir_report(self, sections: list[tuple[str, str]]):
        self.ir_output.clear()
        for title, body in sections:
            self.ir_output.append(f"=== {title} ===\n{body}\n")


class TetradsPolizPanel(QWidget):

    errorClicked = pyqtSignal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "font-weight: 600; padding: 6px 8px; background: #f5f5f5; border-bottom: 1px solid #ddd;"
        )
        layout.addWidget(self.status_label)

        self.error_table = ExprGrammarErrorTable()
        self.error_table.errorClicked.connect(self.errorClicked.emit)

        self.quad_table = QuadTable()

        self.poliz_output = QTextEdit()
        self.poliz_output.setReadOnly(True)
        self.poliz_output.setPlaceholderText(
            "ПОЛИЗ и результат вычисления появятся для выражений из целых чисел…"
        )

        self.tetrads_poliz_splitter = QSplitter(Qt.Orientation.Vertical)
        self.tetrads_poliz_splitter.addWidget(self.quad_table)
        self.tetrads_poliz_splitter.addWidget(self.poliz_output)
        self.tetrads_poliz_splitter.setSizes([280, 320])

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(self.error_table)
        self.main_splitter.addWidget(self.tetrads_poliz_splitter)
        self.main_splitter.setSizes([220, 380])

        layout.addWidget(self.main_splitter)

    def clear(self):
        self.status_label.clear()
        self.error_table.clear_table()
        self.quad_table.clear_table()
        self.poliz_output.clear()

    def set_status(self, text: str, *, success: bool = True):
        color = "#1e7e34" if success else "#c62828"
        self.status_label.setStyleSheet(
            f"font-weight: 600; padding: 6px 8px; color: {color}; "
            "background: #f5f5f5; border-bottom: 1px solid #ddd;"
        )
        self.status_label.setText(text)

    def set_quads(self, quads):
        self.quad_table.clear_table()
        for quad in quads:
            self.quad_table.add_quad(quad)

    def set_poliz(self, rpn, value, warning: str = "", quad_opt_sections: list[tuple[str, str]] | None = None):
        self.poliz_output.clear()
        self.poliz_output.append("ПОЛИЗ и вычисление (только для целых литералов)\n")
        if warning:
            self.poliz_output.append(f"⚠ {warning}\n")
        if rpn:
            self.poliz_output.append(f"ПОЛИЗ: {' '.join(rpn)}")
            val_text = str(value) if value is not None else "—"
            self.poliz_output.append(f"\nЗначение: {val_text}")
        else:
            self.poliz_output.append("ПОЛИЗ: —")
            self.poliz_output.append("\nЗначение: —")
        if quad_opt_sections:
            self.poliz_output.append("\n--- Локальные оптимизации тетрад ---\n")
            for title, body in quad_opt_sections:
                self.poliz_output.append(f"=== {title} ===\n{body}\n")


def create_icon(char):
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 14))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, char)
    painter.end()
    return QIcon(pixmap)


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.text_changed = False
        self.scanner = Scanner()
        self.parser = Parser()
        self.expr_scanner = ExprScanner()
        self.expr_parser = ExprParser()
        self.i18n = I18n("ru")
        self.font_size = 11
        self._menus = {}
        self._actions = {}
        self.setAcceptDrops(True)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(self.i18n.tr("app_title"))
        self.setGeometry(200, 200, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.create_menu_bar()
        self.create_toolbar()
        self.create_search_panel()
        self.create_editor_tabs()
        self.create_output_tabs()
        
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(self.editor_tabs)
        main_splitter.addWidget(self.output_tabs)
        main_splitter.setSizes([500, 400])
        
        layout.addWidget(self.search_panel)
        layout.addWidget(main_splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel(self.i18n.tr("status_ready"))
        self.status_bar.addWidget(self.status_label)
        self.set_status_message(self.i18n.tr("status_ready"))
        
        self.editor_tabs.currentChanged.connect(self._on_editor_tab_changed)
        self.update_status_from_current_tab()
        self.apply_styles()
        self.apply_font_size()
        self.retranslate_ui()

    def set_status_message(self, message: str, state: str = "idle"):
        colors = {
            "idle": "#000000",
            "success": "#1e7e34",
            "error": "#c62828",
        }
        color = colors.get(state, colors["idle"])
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600;")
        self.status_label.setText(message)

    def _editor_font(self) -> QFont:
        font = QFont("Courier New", self.font_size)
        font.setFixedPitch(True)
        return font

    def _apply_font_to_text_edit(self, widget: QTextEdit, font: QFont):
        widget.setFont(font)
        widget.document().setDefaultFont(font)
        cursor = QTextCursor(widget.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFont(font)
        cursor.setCharFormat(fmt)
        cursor.clearSelection()
        cursor.endEditBlock()

    def apply_font_size(self):
        font = self._editor_font()
        for i in range(self.editor_tabs.count()):
            tab = self.editor_tabs.widget(i)
            if tab:
                tab.set_font_size(self.font_size)
        for widget in (
            self.output_area,
            self.ast_output,
            self.ir_optimization_panel.ir_output,
            self.tetrads_poliz_panel.poliz_output,
        ):
            self._apply_font_to_text_edit(widget, font)

    def increase_font_size(self):
        if self.font_size >= 48:
            return
        self.font_size += 1
        self.apply_font_size()
        self._show_font_size_status()

    def decrease_font_size(self):
        if self.font_size <= 6:
            return
        self.font_size -= 1
        self.apply_font_size()
        self._show_font_size_status()

    def reset_font_size(self):
        self.font_size = 11
        self.apply_font_size()
        self._show_font_size_status()

    def _show_font_size_status(self):
        self.set_status_message(f"{self.i18n.tr('font_size_status')}: {self.font_size} pt")

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def set_language(self, lang: str):
        self.i18n.set_language(lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.setWindowTitle(self.i18n.tr("app_title"))
        self._menus["file"].setTitle(self.i18n.tr("menu_file"))
        self._menus["edit"].setTitle(self.i18n.tr("menu_edit"))
        self._menus["view"].setTitle(self.i18n.tr("menu_view"))
        self._menus["text"].setTitle(self.i18n.tr("menu_text"))
        self._menus["run"].setTitle(self.i18n.tr("menu_run"))
        self._menus["help"].setTitle(self.i18n.tr("menu_help"))
        self._menus["language"].setTitle(self.i18n.tr("menu_language"))

        action_keys = {
            "new": "action_new",
            "open": "action_open",
            "save": "action_save",
            "save_as": "action_save_as",
            "new_tab": "action_new_tab",
            "close_tab": "action_close_tab",
            "exit": "action_exit",
            "undo": "action_undo",
            "redo": "action_redo",
            "cut": "action_cut",
            "copy": "action_copy",
            "paste": "action_paste",
            "delete": "action_delete",
            "select_all": "action_select_all",
            "find": "action_find",
            "find_next": "action_find",
            "font_increase": "action_font_increase",
            "font_decrease": "action_font_decrease",
            "font_reset": "action_font_reset",
            "lang_ru": "lang_ru",
            "lang_en": "lang_en",
            "task": "task_action",
            "grammar": "grammar_action",
            "classification": "classification_action",
            "method": "method_action",
            "example": "example_action",
            "references": "references_action",
            "source": "source_action",
            "coursework": "coursework_action",
            "run": "action_run",
            "expr": "action_expr",
            "help": "action_help",
            "shortcuts": "action_shortcuts",
            "about": "action_about",
            "tb_new": "toolbar_new",
            "tb_open": "toolbar_open",
            "tb_save": "toolbar_save",
            "tb_run": "toolbar_run",
            "tb_expr": "toolbar_expr",
            "tb_help": "toolbar_help",
            "tb_about": "action_about",
        }
        for key, tr_key in action_keys.items():
            if key in self._actions:
                self._actions[key].setText(self.i18n.tr(tr_key))

        output_tab_keys = [
            "tab_results",
            "tab_tokens",
            "tab_syntax_errors",
            "tab_search_results",
            "tab_semantics_ast",
            "tab_tetrads_poliz",
            "tab_ir_opt",
        ]
        for idx, tr_key in enumerate(output_tab_keys):
            if idx < self.output_tabs.count():
                self.output_tabs.setTabText(idx, self.i18n.tr(tr_key))

        self.token_table.set_header_labels([
            self.i18n.tr("col_code"),
            self.i18n.tr("col_type"),
            self.i18n.tr("col_lexeme"),
            self.i18n.tr("col_location"),
        ])
        self.syntax_error_table.set_header_labels([
            self.i18n.tr("col_fragment"),
            self.i18n.tr("col_location"),
            self.i18n.tr("col_error_desc"),
        ])
        self.search_result_table.set_header_labels([
            self.i18n.tr("col_match"),
            self.i18n.tr("col_location"),
            self.i18n.tr("col_length"),
        ])
        self.semantic_table.set_header_labels([
            self.i18n.tr("col_fragment"),
            self.i18n.tr("col_location"),
            self.i18n.tr("col_sem_desc"),
        ])

        self.search_find_label.setText(self.i18n.tr("search_find"))
        self.search_input.setPlaceholderText(self.i18n.tr("search_placeholder"))
        self.search_regex_label.setText(self.i18n.tr("search_regex_presets"))
        self.search_type_label.setText(self.i18n.tr("search_type"))
        self.search_button.setText(self.i18n.tr("search_button"))
        self._update_search_count_label(0)

        current_type = self.search_type.currentIndex()
        self.search_type.clear()
        self.search_type.addItems([
            self.i18n.tr("search_type_plain"),
            self.i18n.tr("search_type_regex"),
            self.i18n.tr("search_type_word"),
        ])
        if 0 <= current_type < self.search_type.count():
            self.search_type.setCurrentIndex(current_type)

        preset_idx = self.regex_presets.currentIndex()
        self.regex_presets.setItemText(0, self.i18n.tr("search_regex_choose"))
        if preset_idx >= 0:
            self.regex_presets.setCurrentIndex(preset_idx)

        self.output_area.setPlaceholderText(self.i18n.tr("output_placeholder"))
        self.ast_output.setPlaceholderText(self.i18n.tr("ast_placeholder"))
        self.ir_optimization_panel.ir_output.setPlaceholderText(self.i18n.tr("ir_placeholder"))
        self.tetrads_poliz_panel.poliz_output.setPlaceholderText(self.i18n.tr("poliz_placeholder"))

        for i in range(self.editor_tabs.count()):
            tab = self.editor_tabs.widget(i)
            if tab and not tab.current_file:
                self.editor_tabs.setTabText(i, self.i18n.tr("tab_new_file"))
            if tab:
                tab.set_editor_placeholder(self.i18n.tr("editor_placeholder"))

    def _update_search_count_label(self, count: int):
        self.search_count_label.setText(self.i18n.tr("search_count", count=count))

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.Type.KeyPress
            and isinstance(watched, (CodeEditor, QTextEdit))
            and self._handle_font_zoom_key(event)
        ):
            return True
        return super().eventFilter(watched, event)

    def _handle_font_zoom_key(self, event: QKeyEvent) -> bool:
        if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
            return False
        key = event.key()
        if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            self.decrease_font_size()
            return True
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.increase_font_size()
            return True
        return False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and os.path.isfile(path):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                self.create_new_editor_tab(path)
                self.set_status_message(
                    self.i18n.tr("drop_opened", name=os.path.basename(path))
                )
        event.acceptProposedAction()

    def show_shortcuts(self):
        QMessageBox.information(
            self,
            self.i18n.tr("shortcuts_title"),
            self.i18n.tr("shortcuts_body"),
        )

    def _format_lex_error_message(self, value: str) -> str:
        if value and len(value) > 1 and all(ch == value[0] for ch in value):
            frag = f"недопустимый символ '{value[0]}' (повторение: {len(value)} раза)"
        else:
            frag = f"недопустимый символ '{value}'"
        return f"Лексическая ошибка: {frag}"
        
    def create_search_panel(self):
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(10, 5, 10, 5)
        
        self.search_find_label = QLabel()
        search_layout.addWidget(self.search_find_label)
        
        self.search_input = QLineEdit()
        self.search_input.setMinimumWidth(300)
        self.search_input.returnPressed.connect(self.run_search)
        search_layout.addWidget(self.search_input)

        self.search_regex_label = QLabel()
        search_layout.addWidget(self.search_regex_label)

        self.regex_presets = QComboBox()
        self.regex_presets.setToolTip("RegExp presets")
        self.regex_presets.addItem("", "")
        self.regex_presets.addItem("FR phone", r"^(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}$")
        self.regex_presets.addItem("snake_case", r"^[a-z]+(?:_[a-z]+)*$")
        self.regex_presets.addItem(
            "strong password",
            r"^(?=.*[А-ЯЁ])(?=.*[а-яё])(?=.*\d)(?=.*[()#?!|/@/$%\^&*\-_]).{14,}$",
        )
        self.regex_presets.currentIndexChanged.connect(self.on_regex_preset_changed)
        search_layout.addWidget(self.regex_presets)
        
        self.search_type_label = QLabel()
        search_layout.addWidget(self.search_type_label)
        
        self.search_type = QComboBox()
        search_layout.addWidget(self.search_type)
        
        self.search_button = QPushButton()
        self.search_button.clicked.connect(self.run_search)
        self.search_button.setFixedWidth(80)
        search_layout.addWidget(self.search_button)
        
        self.search_count_label = QLabel()
        self.search_count_label.setFixedWidth(120)
        search_layout.addWidget(self.search_count_label)
        
        search_layout.addStretch()

    def on_regex_preset_changed(self):
        pattern = self.regex_presets.currentData()
        if not pattern:
            return
        self.search_input.setText(pattern)
        self.search_type.setCurrentIndex(1)
        
    def create_editor_tabs(self):
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
        self.editor_tabs.setMovable(True)
        self.create_new_editor_tab()
        
    def create_output_tabs(self):
        self.output_tabs = QTabWidget()
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setPlaceholderText("Результаты работы языкового процессора...")
        self.output_tabs.addTab(self.output_area, "Результаты")
        
        self.token_table = TokenTable()
        self.token_table.tokenClicked.connect(self.go_to_position)
        self.output_tabs.addTab(self.token_table, "Таблица лексем")
        
        self.syntax_error_table = SyntaxErrorTable()
        self.syntax_error_table.errorClicked.connect(self.highlight_error)
        self.output_tabs.addTab(self.syntax_error_table, "Синтаксические ошибки")

        self.search_result_table = SearchResultTable()
        self.search_result_table.resultClicked.connect(self.highlight_search_result)
        self.output_tabs.addTab(self.search_result_table, "Результаты поиска")

        self.semantic_table = SemanticTable()
        self.semantic_table.semanticClicked.connect(self.go_to_position)

        self.ast_output = QTextEdit()
        self.ast_output.setReadOnly(True)
        self.ast_output.setPlaceholderText(
            "Дерево AST появится после успешного синтаксического анализа…"
        )

        self.semantics_ast_splitter = QSplitter(Qt.Orientation.Vertical)
        self.semantics_ast_splitter.addWidget(self.semantic_table)
        self.semantics_ast_splitter.addWidget(self.ast_output)
        self.semantics_ast_splitter.setSizes([220, 380])

        self.semantics_ast_panel = QWidget()
        semantics_ast_layout = QVBoxLayout(self.semantics_ast_panel)
        semantics_ast_layout.setContentsMargins(0, 0, 0, 0)
        semantics_ast_layout.setSpacing(0)
        semantics_ast_layout.addWidget(self.semantics_ast_splitter)

        self.output_tabs.addTab(self.semantics_ast_panel, "Семантика и AST")
        self.tab_semantics_ast = self.output_tabs.count() - 1

        self.tetrads_poliz_panel = TetradsPolizPanel()
        self.tetrads_poliz_panel.errorClicked.connect(self.highlight_error)

        self.tetrads_poliz_tab = QWidget()
        tetrads_poliz_layout = QVBoxLayout(self.tetrads_poliz_tab)
        tetrads_poliz_layout.setContentsMargins(0, 0, 0, 0)
        tetrads_poliz_layout.setSpacing(0)
        tetrads_poliz_layout.addWidget(self.tetrads_poliz_panel)

        self.output_tabs.addTab(self.tetrads_poliz_tab, "Тетрады и ПОЛИЗ")
        self.tab_tetrads_poliz = self.output_tabs.count() - 1

        self.ir_optimization_panel = IrOptimizationPanel()
        self.output_tabs.addTab(self.ir_optimization_panel, "IR и оптимизация")
        self.tab_ir_opt = self.output_tabs.count() - 1

        for widget in (
            self.output_area,
            self.ast_output,
            self.ir_optimization_panel.ir_output,
            self.tetrads_poliz_panel.poliz_output,
        ):
            widget.installEventFilter(self)

    def create_new_editor_tab(self, file_path=None):
        tab = EditorTab()
        tab.textChanged.connect(self.on_text_changed)
        tab.editor.cursorPositionChanged.connect(self.update_status_from_current_tab)
        tab.editor.installEventFilter(self)
        tab.set_font_size(self.font_size)
        tab.set_editor_placeholder(self.i18n.tr("editor_placeholder"))
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    tab.set_text(file.read())
                tab.current_file = file_path
                tab_name = os.path.basename(file_path)
            except Exception as e:
                QMessageBox.critical(
                    self, self.i18n.tr("msg_error"),
                    self.i18n.tr("msg_open_failed", err=str(e)),
                )
                tab_name = self.i18n.tr("tab_new_file")
        else:
            tab_name = self.i18n.tr("tab_new_file")
        
        index = self.editor_tabs.addTab(tab, tab_name)
        self.editor_tabs.setCurrentIndex(index)
        
        return tab

    def _on_editor_tab_changed(self, _index):
        self.update_status_from_current_tab()

    def close_current_editor_tab(self):
        self.close_editor_tab(self.editor_tabs.currentIndex())

    def close_editor_tab(self, index):
        if self.editor_tabs.count() <= 1:
            QMessageBox.information(
                self, self.i18n.tr("msg_info"), self.i18n.tr("msg_cannot_close_last")
            )
            return
            
        tab = self.editor_tabs.widget(index)
        if tab.has_changes():
            reply = QMessageBox.question(
                self, self.i18n.tr("msg_save_title"),
                self.i18n.tr(
                    "msg_save_prompt", name=self.editor_tabs.tabText(index)
                ),
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.editor_tabs.setCurrentIndex(index)
                if not self.save_file():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        self.editor_tabs.removeTab(index)
        
    def get_current_editor_tab(self):
        return self.editor_tabs.currentWidget()
        
    def apply_styles(self):
        self.setStyleSheet("""
            QToolBar {
                background-color: #2c3e50;
                border: none;
                padding: 4px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 4px;
                margin: 1px;
                font-size: 11px;
            }
            QToolBar QToolButton:hover {
                background-color: #34495e;
                border-radius: 3px;
            }
            QToolBar QToolButton:pressed {
                background-color: #3d566e;
            }
            QMenuBar {
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QMenuBar::item:selected {
                background-color: #bdc3c7;
            }
            QStatusBar {
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QPlainTextEdit, QTextEdit {
                background-color: white;
                color: #2c3e50;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-top: none;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                color: #2c3e50;
                padding: 8px 25px 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover:!selected {
                background: #bdc3c7;
            }
            QTabBar::close-button {
                subcontrol-position: right;
                padding: 2px;
            }
            QTabBar::close-button:hover {
                background: #e74c3c;
                border-radius: 2px;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
                color: #212529;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #212529;
            }
            QHeaderView::section {
                background-color: #e9ecef;
                color: #495057;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
            QTableCornerButton::section {
                background-color: #e9ecef;
                border: 1px solid #dee2e6;
            }
            QLineEdit {
                padding: 4px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
            QComboBox {
                padding: 4px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                min-width: 150px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
    def _register_action(self, key: str, action: QAction):
        self._actions[key] = action

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("")
        self._menus["file"] = file_menu
        
        new_action = QAction("", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        self._register_action("new", new_action)
        
        open_action = QAction("", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        self._register_action("open", open_action)
        
        save_action = QAction("", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        self._register_action("save", save_action)
        
        save_as_action = QAction("", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        self._register_action("save_as", save_as_action)

        new_tab_action = QAction("", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(self.new_file)
        file_menu.addAction(new_tab_action)
        self._register_action("new_tab", new_tab_action)

        close_tab_action = QAction("", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(self.close_current_editor_tab)
        file_menu.addAction(close_tab_action)
        self._register_action("close_tab", close_tab_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        self._register_action("exit", exit_action)
        
        edit_menu = menubar.addMenu("")
        self._menus["edit"] = edit_menu
        
        undo_action = QAction("", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        self._register_action("undo", undo_action)
        
        redo_action = QAction("", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        self._register_action("redo", redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)
        self._register_action("cut", cut_action)
        
        copy_action = QAction("", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)
        self._register_action("copy", copy_action)
        
        paste_action = QAction("", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)
        self._register_action("paste", paste_action)
        
        delete_action = QAction("", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_text)
        edit_menu.addAction(delete_action)
        self._register_action("delete", delete_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)
        self._register_action("select_all", select_all_action)

        find_action = QAction("", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.focus_search)
        edit_menu.addAction(find_action)
        self._register_action("find", find_action)

        find_next_action = QAction("", self)
        find_next_action.setShortcut("F3")
        find_next_action.triggered.connect(self.run_search)
        edit_menu.addAction(find_next_action)
        self._register_action("find_next", find_next_action)

        view_menu = menubar.addMenu("")
        self._menus["view"] = view_menu

        font_inc_action = QAction("", self)
        font_inc_action.setShortcuts([
            QKeySequence.StandardKey.ZoomIn,
            QKeySequence("Ctrl+="),
            QKeySequence("Ctrl++"),
        ])
        font_inc_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        font_inc_action.triggered.connect(self.increase_font_size)
        view_menu.addAction(font_inc_action)
        self._register_action("font_increase", font_inc_action)

        font_dec_action = QAction("", self)
        font_dec_action.setShortcuts([
            QKeySequence.StandardKey.ZoomOut,
            QKeySequence(QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Minus)),
            QKeySequence(QKeyCombination(
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
                Qt.Key.Key_Minus,
            )),
            QKeySequence("Ctrl+-"),
        ])
        font_dec_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        font_dec_action.triggered.connect(self.decrease_font_size)
        view_menu.addAction(font_dec_action)
        self._register_action("font_decrease", font_dec_action)

        font_reset_action = QAction("", self)
        font_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        font_reset_action.triggered.connect(self.reset_font_size)
        view_menu.addAction(font_reset_action)
        self._register_action("font_reset", font_reset_action)

        view_menu.addSeparator()
        lang_menu = view_menu.addMenu("")
        self._menus["language"] = lang_menu

        lang_ru_action = QAction("", self)
        lang_ru_action.triggered.connect(lambda: self.set_language("ru"))
        lang_menu.addAction(lang_ru_action)
        self._register_action("lang_ru", lang_ru_action)

        lang_en_action = QAction("", self)
        lang_en_action.triggered.connect(lambda: self.set_language("en"))
        lang_menu.addAction(lang_en_action)
        self._register_action("lang_en", lang_en_action)
        
        text_menu = menubar.addMenu("")
        self._menus["text"] = text_menu
        
        task_action = QAction("", self)
        task_action.triggered.connect(partial(self.show_course_material, "task"))
        text_menu.addAction(task_action)
        self._register_action("task", task_action)
        
        grammar_action = QAction("", self)
        grammar_action.triggered.connect(partial(self.show_course_material, "grammar"))
        text_menu.addAction(grammar_action)
        self._register_action("grammar", grammar_action)
        
        classification_action = QAction("", self)
        classification_action.triggered.connect(partial(self.show_course_material, "classification"))
        text_menu.addAction(classification_action)
        self._register_action("classification", classification_action)
        
        method_action = QAction("", self)
        method_action.triggered.connect(partial(self.show_course_material, "method"))
        text_menu.addAction(method_action)
        self._register_action("method", method_action)
        
        example_action = QAction("", self)
        example_action.triggered.connect(partial(self.show_course_material, "example"))
        text_menu.addAction(example_action)
        self._register_action("example", example_action)
        
        references_action = QAction("", self)
        references_action.triggered.connect(partial(self.show_course_material, "references"))
        text_menu.addAction(references_action)
        self._register_action("references", references_action)
        
        source_action = QAction("", self)
        source_action.triggered.connect(partial(self.show_course_material, "source"))
        text_menu.addAction(source_action)
        self._register_action("source", source_action)
        
        coursework_action = QAction("", self)
        coursework_action.triggered.connect(partial(self.show_course_material, "coursework"))
        text_menu.addAction(coursework_action)
        self._register_action("coursework", coursework_action)
        
        run_menu = menubar.addMenu("")
        self._menus["run"] = run_menu

        run_action = QAction("", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_analyzer)
        run_menu.addAction(run_action)
        self._register_action("run", run_action)

        expr_action = QAction("", self)
        expr_action.setShortcut("F6")
        expr_action.triggered.connect(self.run_expr_analyzer)
        run_menu.addAction(expr_action)
        self._register_action("expr", expr_action)

        help_menu = menubar.addMenu("")
        self._menus["help"] = help_menu
        
        help_action = QAction("", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        self._register_action("help", help_action)

        shortcuts_action = QAction("", self)
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        self._register_action("shortcuts", shortcuts_action)
        
        about_action = QAction("", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        self._register_action("about", about_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("Панель инструментов")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        
        new_action = QAction("", self)
        new_icon = QIcon.fromTheme("document-new")
        if new_icon.isNull():
            new_icon = create_icon("📄")
        new_action.setIcon(new_icon)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        self._register_action("tb_new", new_action)
        
        open_action = QAction("", self)
        open_icon = QIcon.fromTheme("document-open")
        if open_icon.isNull():
            open_icon = create_icon("📂")
        open_action.setIcon(open_icon)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        self._register_action("tb_open", open_action)
        
        save_action = QAction("", self)
        save_icon = QIcon.fromTheme("document-save")
        if save_icon.isNull():
            save_icon = create_icon("💾")
        save_action.setIcon(save_icon)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        self._register_action("tb_save", save_action)
        
        toolbar.addSeparator()
        
        undo_action = QAction("", self)
        undo_icon = QIcon.fromTheme("edit-undo")
        if undo_icon.isNull():
            undo_icon = create_icon("↩")
        undo_action.setIcon(undo_icon)
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("", self)
        redo_icon = QIcon.fromTheme("edit-redo")
        if redo_icon.isNull():
            redo_icon = create_icon("↪")
        redo_action.setIcon(redo_icon)
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)
        
        toolbar.addSeparator()
        
        copy_action = QAction("", self)
        copy_icon = QIcon.fromTheme("edit-copy")
        if copy_icon.isNull():
            copy_icon = create_icon("📋")
        copy_action.setIcon(copy_icon)
        copy_action.triggered.connect(self.copy)
        toolbar.addAction(copy_action)
        
        cut_action = QAction("", self)
        cut_icon = QIcon.fromTheme("edit-cut")
        if cut_icon.isNull():
            cut_icon = create_icon("✂")
        cut_action.setIcon(cut_icon)
        cut_action.triggered.connect(self.cut)
        toolbar.addAction(cut_action)
        
        paste_action = QAction("", self)
        paste_icon = QIcon.fromTheme("edit-paste")
        if paste_icon.isNull():
            paste_icon = create_icon("📌")
        paste_action.setIcon(paste_icon)
        paste_action.triggered.connect(self.paste)
        toolbar.addAction(paste_action)
        
        toolbar.addSeparator()
        
        run_action = QAction("", self)
        run_icon = QIcon.fromTheme("media-playback-start")
        if run_icon.isNull():
            run_icon = create_icon("▶")
        run_action.setIcon(run_icon)
        run_action.triggered.connect(self.run_analyzer)
        toolbar.addAction(run_action)
        self._register_action("tb_run", run_action)

        expr_action = QAction("", self)
        expr_icon = QIcon.fromTheme("system-run")
        if expr_icon.isNull():
            expr_icon = create_icon("fx")
        expr_action.setIcon(expr_icon)
        expr_action.triggered.connect(self.run_expr_analyzer)
        toolbar.addAction(expr_action)
        self._register_action("tb_expr", expr_action)

        toolbar.addSeparator()

        help_action = QAction("", self)
        help_icon = QIcon.fromTheme("help-contents")
        if help_icon.isNull():
            help_icon = create_icon("?")
        help_action.setIcon(help_icon)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
        self._register_action("tb_help", help_action)
        
        about_action = QAction("", self)
        about_icon = QIcon.fromTheme("help-about")
        if about_icon.isNull():
            about_icon = create_icon("i")
        about_action.setIcon(about_icon)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
        self._register_action("tb_about", about_action)
    
    def new_file(self):
        self.create_new_editor_tab()
        self.set_status_message(self.i18n.tr("status_new_file"))
        
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.tr("dialog_open"), "",
            self.i18n.tr("filter_text"),
        )
        if file_path:
            self.create_new_editor_tab(file_path)
            self.set_status_message(self.i18n.tr("status_opened", path=file_path))
                    
    def save_file(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return False
            
        if tab.current_file:
            try:
                with open(tab.current_file, 'w', encoding='utf-8') as file:
                    file.write(tab.get_text())
                tab.text_changed = False
                self.set_status_message(
                    self.i18n.tr("status_saved", name=os.path.basename(tab.current_file))
                )
                return True
            except Exception as e:
                QMessageBox.critical(
                    self, self.i18n.tr("msg_error"),
                    self.i18n.tr("msg_save_failed", err=str(e)),
                )
                return False
        else:
            return self.save_file_as()
            
    def save_file_as(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return False
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.i18n.tr("dialog_save_as"), "",
            self.i18n.tr("filter_text"),
        )
        if file_path:
            tab.current_file = file_path
            self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), os.path.basename(file_path))
            return self.save_file()
        return False
        
    def maybe_save(self):
        for i in range(self.editor_tabs.count()):
            tab = self.editor_tabs.widget(i)
            if tab.has_changes():
                self.editor_tabs.setCurrentIndex(i)
                reply = QMessageBox.question(
                    self, self.i18n.tr("msg_save_title"),
                    self.i18n.tr(
                        "msg_save_prompt", name=self.editor_tabs.tabText(i)
                    ),
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard |
                    QMessageBox.StandardButton.Cancel,
                )
                
                if reply == QMessageBox.StandardButton.Save:
                    if not self.save_file():
                        return False
                elif reply == QMessageBox.StandardButton.Cancel:
                    return False
        return True
        
    def closeEvent(self, event):
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()
            
    def on_text_changed(self):
        self.update_status_from_current_tab()
            
    def update_status_from_current_tab(self):
        tab = self.get_current_editor_tab()
        if tab:
            line = tab.get_current_line()
            col = tab.get_current_column()
            chars = len(tab.get_text())
            self.set_status_message(
                self.i18n.tr(
                    "status_line_col_chars", line=line, col=col, chars=chars
                )
            )
        
    def undo(self):
        tab = self.get_current_editor_tab()
        if tab:
            tab.undo()
        
    def redo(self):
        tab = self.get_current_editor_tab()
        if tab:
            tab.redo()
        
    def cut(self):
        tab = self.get_current_editor_tab()
        if tab:
            tab.cut()
        
    def copy(self):
        tab = self.get_current_editor_tab()
        if tab:
            tab.copy()
        
    def paste(self):
        tab = self.get_current_editor_tab()
        if tab:
            tab.paste()
        
    def delete_text(self):
        tab = self.get_current_editor_tab()
        if tab:
            cursor = tab.editor.textCursor()
            if cursor.hasSelection():
                cursor.removeSelectedText()
        
    def select_all(self):
        tab = self.get_current_editor_tab()
        if tab:
            tab.select_all()
    
    def go_to_position(self, line, pos):
        tab = self.get_current_editor_tab()
        if tab:
            tab.go_to_position(line, pos)
    
    def highlight_error(self, line, start_pos, end_pos, row):
        tab = self.get_current_editor_tab()
        if tab:
            tab.go_to_position(line, start_pos)
    
    def highlight_search_result(self, line, start_pos, end_pos):
        tab = self.get_current_editor_tab()
        if tab:
            tab.highlight_search_result(line, start_pos, end_pos)
    
    def run_search(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return
        
        text = tab.get_text()
        search_pattern = self.search_input.text()
        
        if not text.strip():
            QMessageBox.information(
                self, self.i18n.tr("msg_info"), self.i18n.tr("search_no_editor")
            )
            return
        
        self.search_result_table.clear_table()
        tab.clear_highlighting()
        
        search_type = self.search_type.currentIndex()
        
        results = []
        
        lines = text.split('\n')
        
        try:
            if search_type == 0:
                if not search_pattern:
                    QMessageBox.information(
                        self, self.i18n.tr("msg_info"), self.i18n.tr("search_no_pattern")
                    )
                    return
                for line_num, line in enumerate(lines, start=1):
                    pos = 0
                    while True:
                        start = line.find(search_pattern, pos)
                        if start == -1:
                            break
                        end = start + len(search_pattern)
                        results.append((line_num, start + 1, end, search_pattern))
                        pos = end
            
            elif search_type == 1:
                if not search_pattern:
                    QMessageBox.information(
                        self, self.i18n.tr("msg_info"), self.i18n.tr("search_no_regex")
                    )
                    return
                regex = re.compile(search_pattern)
                for line_num, line in enumerate(lines, start=1):
                    for match in regex.finditer(line):
                        start = match.start()
                        end = match.end()
                        results.append((line_num, start + 1, end, match.group()))
            
            elif search_type == 2:
                if not search_pattern:
                    QMessageBox.information(
                        self, self.i18n.tr("msg_info"), self.i18n.tr("search_no_pattern")
                    )
                    return
                word_pattern = r'\b' + re.escape(search_pattern) + r'\b'
                regex = re.compile(word_pattern)
                for line_num, line in enumerate(lines, start=1):
                    for match in regex.finditer(line):
                        start = match.start()
                        end = match.end()
                        results.append((line_num, start + 1, end, match.group()))
            
            for line_num, start_pos, end_pos, match_text in results:
                self.search_result_table.add_result(match_text, line_num, start_pos, end_pos, len(match_text))
            
            count = len(results)
            self._update_search_count_label(count)
            
            if count == 0 and search_pattern:
                QMessageBox.information(
                    self,
                    self.i18n.tr("search_results_title"),
                    self.i18n.tr("search_no_matches", pattern=search_pattern),
                )
            elif count > 0:
                self.output_tabs.setCurrentIndex(3)
                self.set_status_message(
                    self.i18n.tr("search_done", count=count)
                )
                
        except re.error as e:
            QMessageBox.critical(
                self, self.i18n.tr("msg_error"),
                self.i18n.tr("search_regex_error", err=str(e)),
            )
        except Exception as e:
            QMessageBox.critical(
                self, self.i18n.tr("msg_error"),
                self.i18n.tr("search_error", err=str(e)),
            )
    
    def _filter_lex_errors_for_display(
        self, text: str, lex_errors, syntax_errors, absorbed_real_positions=frozenset()
    ) -> list:
        suppress_const_prefix = any(
            err.message.startswith("Ожидалось ключевое слово const")
            for err in syntax_errors
        )
        lex_syn_positions = {
            (err.line, err.pos)
            for err in syntax_errors
            if err.message.startswith("Лексическая ошибка:")
        }
        ident_syn_positions = {
            (err.line, err.pos)
            for err in syntax_errors
            if err.message.startswith("Ожидался идентификатор;")
        } | lex_syn_positions
        colon_idx = text.find(":")
        colon_pos_1based = colon_idx + 1 if colon_idx >= 0 else None
        out = []
        for le in lex_errors:
            if le.type == TokenType.ERROR:
                if suppress_const_prefix and (
                    colon_pos_1based is None or le.start_pos < colon_pos_1based
                ):
                    continue
                if (le.line, le.start_pos) in ident_syn_positions:
                    continue
                if (le.line, le.start_pos) in absorbed_real_positions:
                    continue
            out.append(le)
        return out

    def run_analyzer(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return

        text = tab.get_text()
        if not text.strip():
            QMessageBox.information(
                self, self.i18n.tr("msg_info"), self.i18n.tr("msg_enter_text")
            )
            return

        tab.clear_highlighting()
        self.token_table.clear_table()
        self.syntax_error_table.clear_table()
        self.output_area.clear()
        self.ast_output.clear()
        self.semantic_table.clear_table()
        self.ir_optimization_panel.clear()

        try:
            tokens, lex_errors = self.scanner.analyze(text)

            for token in tokens:
                self.token_table.add_token(token)

            self.output_area.append("=== РЕЗУЛЬТАТЫ ПАРСЕРА ===\n")

            if lex_errors:
                self.output_area.append("Парсер не запущен: обнаружены лексические ошибки.\n")
                self.output_area.append("=== ЛЕКСИЧЕСКИЕ ОШИБКИ ===")
                for error in lex_errors:
                    self.output_area.append(
                        f"! Строка {error.line}, позиция {error.start_pos}: "
                        f"недопустимый символ '{error.value}'"
                    )
                    self.syntax_error_table.add_error(
                        error.value, error.line, error.start_pos, error.end_pos,
                        f"недопустимый символ '{error.value}'",
                    )

                first = lex_errors[0]
                self.go_to_position(first.line, first.start_pos)
                self.output_tabs.setCurrentIndex(2)
                self.set_status_message(
                    f"Анализ завершен. Лексических ошибок: {len(lex_errors)}", "error"
                )
                return

            self.output_area.append("\n=== СИНТАКСИЧЕСКИЙ АНАЛИЗ ===\n")
            ast_root, syntax_errors, semantic_errors, symbol_table = self.parser.analyze_full(tokens)

            if syntax_errors:
                self.output_area.append(f"Найдено синтаксических ошибок: {len(syntax_errors)}\n")
                self.output_area.append("=== СИНТАКСИЧЕСКИЕ ОШИБКИ ===")

                for error in syntax_errors:
                    self.output_area.append(
                        f"! '{error.fragment}' | стр.{error.line}, поз.{error.pos} | {error.message}"
                    )
                    end_pos = (
                        error.pos
                        if error.fragment == "<конец>"
                        else error.pos + len(error.fragment) - 1
                    )
                    self.syntax_error_table.add_error(
                        error.fragment, error.line, error.pos, end_pos, error.message
                    )

                first = syntax_errors[0]
                if first.fragment != "<конец>":
                    end_pos = first.pos + len(first.fragment) - 1
                    self.highlight_error(first.line, first.pos, end_pos, 0)
                else:
                    self.go_to_position(first.line, first.pos)
                self.output_tabs.setCurrentIndex(2)
                self.set_status_message(
                    f"Анализ завершен. Всего ошибок: {len(syntax_errors)}", "error"
                )
                return

            self.output_area.append("Синтаксических ошибок не обнаружено. Строка корректна.")

            self.ast_output.append("=== AST ===\n")
            self.ast_output.append(self.parser.format_ast(ast_root))

            if semantic_errors:
                for error in semantic_errors:
                    self.semantic_table.add_result(
                        error.fragment, error.line, error.pos, error.message, is_error=True
                    )
                    end_pos = (
                        error.pos + len(error.fragment) - 1
                        if error.fragment != "<неизвестно>"
                        else error.pos
                    )
                    self.syntax_error_table.add_error(
                        error.fragment, error.line, error.pos, end_pos, error.message
                    )

                first = semantic_errors[0]
                self.go_to_position(first.line, first.pos)
            else:
                self.semantic_table.add_result(
                    "-", 1, 1, "Семантических ошибок не обнаружено.", is_error=False
                )

            ir_instructions = IrGenerator().generate(ast_root)
            optimization_steps = apply_optimizations(ir_instructions, symbol_table)

            ir_sections: list[tuple[str, str]] = [
                ("Входной IR (трёхадресный код)", format_ir(ir_instructions)),
            ]
            for step in optimization_steps:
                ir_sections.append(
                    (
                        f"Входной IR для «{step.name}»",
                        format_ir(step.before),
                    )
                )
                ir_sections.append(
                    (
                        f"Выходной IR после «{step.name}»",
                        f"{step.description}\n\n{format_ir(step.after)}",
                    )
                )

            self.ir_optimization_panel.set_ir_report(ir_sections)
            self.ir_optimization_panel.set_status(
                "AST построено; TAC сгенерирован; применены 2 локальные оптимизации.",
                success=len(semantic_errors) == 0,
            )

            self.output_area.append("\n=== ПРОМЕЖУТОЧНОЕ ПРЕДСТАВЛЕНИЕ (TAC) ===\n")
            self.output_area.append(format_ir(ir_instructions))
            for step in optimization_steps:
                self.output_area.append(f"\n--- {step.name} ---\n{format_ir(step.after)}")

            self.output_tabs.setCurrentIndex(self.tab_semantics_ast)

            total_errors = len(syntax_errors) + len(semantic_errors)
            self.output_area.append(f"\nКоличество ошибок: {total_errors}")
            status_state = "success" if total_errors == 0 else "error"
            self.set_status_message(f"Анализ завершен. Всего ошибок: {total_errors}", status_state)

            if total_errors == 0:
                self.output_area.append("\n✅ Программа синтаксически и семантически верна!")
                self.output_tabs.setCurrentIndex(self.tab_ir_opt)

        except Exception as e:
            import traceback
            self.output_area.append(f"Ошибка при анализе: {str(e)}")
            self.output_area.append(traceback.format_exc())
            self.set_status_message("Ошибка при анализе", "error")

    def run_expr_analyzer(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return

        text = tab.get_text().strip()
        if not text:
            QMessageBox.information(
                self, self.i18n.tr("msg_info"), self.i18n.tr("msg_enter_expr")
            )
            return

        tab.clear_highlighting()
        self.token_table.clear_table()
        self.syntax_error_table.clear_table()
        self.output_area.clear()
        self.tetrads_poliz_panel.clear()

        try:
            tokens, lex_errors = self.expr_scanner.analyze(text)

            for token in tokens:
                if token.type.name != "WHITESPACE":
                    self.token_table.add_token(token)

            self.output_area.append("=== АРИФМЕТИЧЕСКОЕ ВЫРАЖЕНИЕ ===\n")
            self.output_area.append(f"Вход: {text}\n")
            self.output_area.append("=== ЛЕКСИЧЕСКИЙ АНАЛИЗ ===\n")
            meaningful = [t for t in tokens if t.type.name != "WHITESPACE"]
            self.output_area.append(f"Всего лексем: {len(meaningful)}")

            if lex_errors:
                self.output_area.append(f"Лексических ошибок: {len(lex_errors)}\n")
                self.output_area.append(
                    "⚠ Генерация тетрад и ПОЛИЗ пропущена: обнаружены лексические ошибки.\n"
                )
                self.output_area.append("=== ЛЕКСИЧЕСКИЕ ОШИБКИ ===")
                self.tetrads_poliz_panel.set_status(
                    "Лексические ошибки: тетрады и ПОЛИЗ не построены.", success=False
                )
                for error in lex_errors:
                    msg = f"недопустимый символ '{error.value}'"
                    self.output_area.append(
                        f"! Строка {error.line}, позиция {error.start_pos}: {msg}"
                    )
                    self.syntax_error_table.add_error(
                        error.value, error.line, error.start_pos, error.end_pos, msg
                    )
                    self.tetrads_poliz_panel.error_table.add_error(
                        error.value, error.line, error.start_pos, error.end_pos, msg
                    )
                first = lex_errors[0]
                self.go_to_position(first.line, first.start_pos)
                self.output_tabs.setCurrentIndex(self.tab_tetrads_poliz)
                self.set_status_message(
                    f"Анализ выражения: лексических ошибок — {len(lex_errors)}", "error"
                )
                return

            self.output_area.append("Лексических ошибок не обнаружено.\n")
            self.output_area.append("=== СИНТАКСИЧЕСКИЙ АНАЛИЗ (рекурсивный спуск) ===\n")

            result, quads, rpn, value, syn_errors, warning = self.expr_parser.analyze(tokens)

            if syn_errors:
                self.output_area.append(
                    f"Найдено синтаксических ошибок: {len(syn_errors)}\n"
                )
                self.output_area.append(
                    "⚠ Генерация тетрад и ПОЛИЗ пропущена: обнаружены синтаксические ошибки.\n"
                )
                self.output_area.append("=== СИНТАКСИЧЕСКИЕ ОШИБКИ ===")
                self.tetrads_poliz_panel.set_status(
                    "Синтаксические ошибки: тетрады и ПОЛИЗ не построены.", success=False
                )
                for error in syn_errors:
                    self.output_area.append(
                        f"! '{error.fragment}' | стр.{error.line}, поз.{error.pos} | {error.message}"
                    )
                    end_pos = (
                        error.pos
                        if error.fragment == "<конец>"
                        else error.pos + len(error.fragment) - 1
                    )
                    self.syntax_error_table.add_error(
                        error.fragment, error.line, error.pos, end_pos, error.message
                    )
                    self.tetrads_poliz_panel.error_table.add_error(
                        error.fragment, error.line, error.pos, end_pos, error.message
                    )
                first = syn_errors[0]
                if first.fragment != "<конец>":
                    end_pos = first.pos + len(first.fragment) - 1
                    self.highlight_error(first.line, first.pos, end_pos, 0)
                else:
                    self.go_to_position(first.line, first.pos)
                self.output_tabs.setCurrentIndex(self.tab_tetrads_poliz)
                self.set_status_message(
                    f"Анализ выражения: синтаксических ошибок — {len(syn_errors)}", "error"
                )
                return

            self.output_area.append("Синтаксических ошибок не обнаружено. Выражение корректно.")
            if result:
                self.output_area.append(f"Результат выражения (имя/временная): {result}\n")

            self.tetrads_poliz_panel.set_status(
                "Арифметическое выражение по грамматике E→TA разобрано без ошибок; тетрады построены.",
                success=True,
            )
            self.tetrads_poliz_panel.error_table.show_no_errors()
            self.tetrads_poliz_panel.set_quads(quads)

            quad_opt_sections: list[tuple[str, str]] = []
            if quads:
                quad_steps = apply_quad_optimizations(quads)
                quad_opt_sections.append(("Входной IR (тетрады)", format_quads(quads)))
                for step in quad_steps:
                    quad_opt_sections.append((f"Входной IR для «{step.name}»", format_quads(step.before)))
                    quad_opt_sections.append(
                        (
                            f"Выходной IR после «{step.name}»",
                            f"{step.description}\n\n{format_quads(step.after)}",
                        )
                    )
                self.tetrads_poliz_panel.set_quads(quad_steps[-1].after)

            self.output_area.append("=== ТЕТРАДЫ (входной IR) ===\n")
            if quads:
                self.output_area.append(format_quads(quads))
                for step in quad_steps:
                    self.output_area.append(f"\n--- {step.name} ---\n{format_quads(step.after)}")
            else:
                self.output_area.append("(тетрады не сгенерированы)")

            self.tetrads_poliz_panel.set_poliz(rpn, value, warning, quad_opt_sections)
            if warning:
                self.output_area.append(f"\n⚠ {warning}")
            if rpn:
                rpn_str = " ".join(rpn)
                self.output_area.append(f"\n=== ПОЛИЗ ===\n{rpn_str}")
                self.output_area.append(f"Значение: {value}")

            self.output_tabs.setCurrentIndex(self.tab_tetrads_poliz)
            self.set_status_message("Анализ арифметического выражения завершён успешно", "success")
            if not warning and quads:
                self.output_area.append("\n✅ Выражение разобрано, тетрады и ПОЛИЗ построены.")

        except Exception as e:
            import traceback
            self.output_area.append(f"Ошибка при анализе выражения: {str(e)}")
            self.output_area.append(traceback.format_exc())
            self.set_status_message("Ошибка при анализе выражения", "error")
    
    def _course_asset_href(self, filename: str) -> str:
        path = os.path.join(_course_assets_base_dir(), filename)
        if not os.path.isfile(path):
            return ""
        return QUrl.fromLocalFile(os.path.abspath(path)).toString()

    def _course_img_html(self, filename: str, alt: str) -> str:
        href = self._course_asset_href(filename)
        if not href:
            return (
                f"<p><i>Файл изображения «{filename}» не найден в папке "
                f"<span class='mono'>text_editor/assets</span>.</i></p>"
            )
        return f'<p><img src="{href}" alt="{alt}"/></p>'

    def _show_course_dialog(self, title: str, inner_html: str) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        doc = (
            "<html><head><meta charset=\"utf-8\"/>"
            "<style>"
            "body{font-family:'Segoe UI',Arial,sans-serif;font-size:11pt;line-height:1.45;margin:8px;}"
            "h2{font-size:13pt;margin-top:0;} h3{font-size:12pt;}"
            "ol{padding-left:1.35em;} ul{padding-left:1.35em;} "
            ".mono{font-family:Consolas,'Courier New',monospace;font-size:10.5pt;}"
            "img{max-width:100%;height:auto;}"
            "</style></head><body>"
            f"{inner_html}</body></html>"
        )
        browser.setHtml(doc)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.resize(880, 640)
        dlg.exec()

    def show_course_material(self, section_id: str) -> None:
        img_auto = self._course_img_html("automaton.png", "Граф автомата")
        img_ok = self._course_img_html("test_example_ok.png", "Корректный пример")
        img_err = self._course_img_html("test_example_errors.png", "Пример с ошибками")

        bodies = {
            "task": """
<h2>Постановка задачи</h2>
<p>Вещественные константы — это числа, содержащие целую и дробную части, разделённые
десятичной точкой, значение которых не меняется в процессе выполнения программы.</p>
<p>Для описания вещественных констант в языке Pascal используется служебное слово
<code class='mono'>const</code>.</p>
<p><b>Формат записи:</b> <code class='mono'>const имя_константы: real = значение;</code></p>
<p><b>Примеры:</b></p>
<ol>
<li>Простое объявление вещественной константы: <code class='mono'>const pi: real = 3.14;</code></li>
<li>Объявление вещественной константы числа <i>e</i>:
<code class='mono'>const e: real = 2.71828;</code></li>
</ol>
<p>В связи с разработанной автоматной грамматикой G[‹START›] синтаксический анализатор
(парсер) объявлений вещественных констант будет считать верными следующие записи:</p>
<ol>
<li><code class='mono'>const pi: real = 3.14;</code></li>
<li><code class='mono'>const x: real = 0.5;</code></li>
<li><code class='mono'>const myConst: real = 10.0;</code></li>
<li><code class='mono'>const _gravity: real = 9.81;</code></li>
</ol>
""",
            "grammar": """
<h2>Грамматика</h2>
<ol>
<li>‹START› → <code class='mono'>const</code> &lt;SPACE&gt;</li>
<li>&lt;SPACE&gt; → <code class='mono'>_</code> &lt;ID&gt;</li>
<li>&lt;ID&gt; → letter &lt;ID_REST&gt;</li>
<li>&lt;ID_REST&gt; → letter &lt;ID_REST&gt; | &lt;COLON&gt;</li>
<li>&lt;COLON&gt; → <code class='mono'>:</code> &lt;TYPE&gt;</li>
<li>&lt;TYPE&gt; → <code class='mono'>real</code> &lt;EQUALS&gt;</li>
<li>&lt;EQUALS&gt; → <code class='mono'>=</code> &lt;NUMBER&gt;</li>
<li>&lt;NUMBER&gt; → digit &lt;INT_REST&gt;</li>
<li>&lt;INT_REST&gt; → digit &lt;INT_REST&gt; | <code class='mono'>.</code> &lt;FRAC_PART&gt;</li>
<li>&lt;FRAC_PART&gt; → digit &lt;FRAC_REST&gt;</li>
<li>&lt;FRAC_REST&gt; → digit &lt;SEMICOLON&gt;</li>
<li>&lt;SEMICOLON&gt; → <code class='mono'>;</code></li>
</ol>
<p>Следуя формальному определению грамматики, представим G[‹START›] её составляющими:</p>
<ul>
<li><b>Vt</b> = { <code class='mono'>const</code>, a…z, A…Z, <code class='mono'>_</code>,
<code class='mono'>:</code>, <code class='mono'>real</code>, <code class='mono'>=</code>,
0…9, <code class='mono'>.</code>, <code class='mono'>;</code> }</li>
<li><b>Vn</b> = { &lt;START&gt;, &lt;SPACE&gt;, &lt;ID&gt;, &lt;ID_REST&gt;, &lt;COLON&gt;, &lt;TYPE&gt;,
&lt;EQUALS&gt;, &lt;NUMBER&gt;, &lt;INT_REST&gt;, &lt;FRAC_PART&gt;, &lt;FRAC_REST&gt;, &lt;SEMICOLON&gt; }</li>
</ul>
""",
            "classification": """
<h2>Классификация грамматики</h2>
<p>Согласно классификации Хомского, грамматика G[‹START›] является <b>автоматной</b>,
так как все продукции имеют вид A → aB или A → a:</p>
<p class='mono'>G[A]: A → aB | a | Λ , a ∈ VT,  A, B ∈ VN.</p>
<ul>
<li><b>A → aB | a | Λ</b> — три варианта правил для нетерминала A:
<ul>
<li><b>A → aB</b> — терминал a, за которым следует нетерминал B.</li>
<li><b>A → a</b> — одиночный терминал a.</li>
<li><b>A → Λ</b> — пустая цепочка (ε-правило).</li>
</ul></li>
<li><b>a ∈ VT</b> — терминал.</li>
<li><b>A, B ∈ VN</b> — нетерминалы.</li>
</ul>
""",
            "method": f"""
<h2>Метод анализа</h2>
<p>Грамматика G[‹START›] является автоматной. Правила (1)–(11) для G[‹START›]
реализованы на графе конечного автомата (см. рисунок 1).</p>
<p>Сплошные стрелки на графе соответствуют синтаксически верному разбору объявлений
вещественных констант языка Pascal; конечное состояние автомата означает успешное
завершение разбора конструкции.</p>
<h3>Рисунок 1. Граф метода анализа (конечный автомат)</h3>
{img_auto}
""",
            "example": f"""
<h2>Тестовый пример</h2>
<p>Ниже приведены скриншоты работы приложения: успешный разбор корректной строки и
разбор строки с несколькими синтаксическими ошибками.</p>
<h3>Корректная строка</h3>
<p><code class='mono'>const pi: real = 3.14;</code></p>
{img_ok}
<h3>Строка с ошибками</h3>
<p><code class='mono'>1 const pi real === 3.;</code></p>
{img_err}
""",
            "references": """
<h2>Список литературы</h2>
<ol>
<li>Шорников Ю.В. Теория и практика языковых процессоров : учеб. пособие / Ю.В. Шорников.
— Новосибирск: Изд-во НГТУ, 2022.</li>
<li>Gries D. Designing Compilers for Digital Computers. New York, Jhon Wiley, 1971. 493 p.</li>
<li>Теория формальных языков и компиляторов [Электронный ресурс] / Электрон. дан.
URL: <a href="https://dispace.edu.nstu.ru/didesk/course/show/8594">https://dispace.edu.nstu.ru/didesk/course/show/8594</a>,
свободный. Яз. рус. (дата обращения 10.04.2026).</li>
</ol>
""",
            "source": """
<h2>Исходный код программы</h2>
<p>Репозиторий с исходным кодом на ветке <code class='mono'>kurs_fp</code>:</p>
<p><a href="https://github.com/etnight15/Complier/tree/kurs_fp">https://github.com/etnight15/Complier/tree/kurs_fp</a></p>
""",
            "coursework": """
<h2>Курсовая работа</h2>
<p>Текст курсовой работы (Google Документы):</p>
<p><a href="https://docs.google.com/document/d/1Kh1SSd_CD1VtqBUpuyMuwOhlihFwMrVO/edit?usp=sharing&amp;ouid=115459672282642477363&amp;rtpof=true&amp;sd=true">Открыть документ на Google Диске</a></p>
""",
        }
        titles = {
            "task": "Постановка задачи",
            "grammar": "Грамматика",
            "classification": "Классификация грамматики",
            "method": "Метод анализа",
            "example": "Тестовый пример",
            "references": "Список литературы",
            "source": "Исходный код программы",
            "coursework": "Курсовая работа",
        }
        inner = bodies.get(section_id)
        if inner is None:
            QMessageBox.warning(self, "Ошибка", "Неизвестный раздел материалов.")
            return
        self._show_course_dialog(titles[section_id], inner)

    def show_help(self):
        help_text = """
        Анализ (Пуск, F5):
        - Лексический и синтаксический анализ объявлений const
        - Построение AST и семантическая проверка
        - Генерация трёхадресного кода (TAC) и две локальные оптимизации (вкладка «IR и оптимизация»)
        
        Анализ выражения (F6):
        - Разбор арифметического выражения, тетрады и ПОЛИЗ
        
        Команды меню Файл:
        - Создать (Ctrl+N) - создание нового файла
        - Открыть (Ctrl+O) - открытие существующего файла
        - Сохранить (Ctrl+S) - сохранение текущего файла
        - Сохранить как (Ctrl+Shift+S) - сохранение под новым именем
        - Выход (Ctrl+Q) - выход из программы
        
        Команды меню Правка:
        - Отмена (Ctrl+Z) - отмена последнего действия
        - Повтор (Ctrl+Y) - повтор отмененного действия
        - Вырезать (Ctrl+X) - вырезать выделенный текст
        - Копировать (Ctrl+C) - копировать выделенный текст
        - Вставить (Ctrl+V) - вставить из буфера обмена
        - Удалить (Del) - удалить выделенный текст
        - Выделить все (Ctrl+A) - выделить весь текст
        
        Назначение программы:
        - Лексический и синтаксический анализ (F5) — объявления const
        - Семантика, AST, TAC и локальные оптимизации (вкладка IR)
        - Арифметические выражения, тетрады, ПОЛИЗ (F6)
        """
        
        QMessageBox.information(self, "Справка", help_text)
        
    def show_about(self):
        about_text = (
            "<div style='font-size: 11pt; line-height: 1.45;'>"
            "<h3 style='margin-bottom: 8px;'>Compiler</h3>"
            "<p><b>Студент:</b> Марков Данил Дмитриевич<br>"
            "<b>Год:</b> 2026<br>"
            "<b>Вариант курсовой работы:</b> Объявление вещественной константы с "
            "инициализацией на языке Pascal</p>"
            "<p>ЛР5–7: объявления <code>const</code>, AST, семантика, трёхадресный код "
            "и две локальные оптимизации (F5). Арифметические выражения — тетрады и ПОЛИЗ (F6).</p>"
            "</div>"
        )
        QMessageBox.about(self, "О программе", about_text)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Compiler")
    app.setApplicationDisplayName("Compiler")
    app.setOrganizationName("Student")
    
    window = TextEditor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()