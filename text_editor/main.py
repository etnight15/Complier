import sys
import os
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QTextEdit, QToolBar, QMenu, QFileDialog, QMessageBox, 
                             QSplitter, QStatusBar, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabWidget, QComboBox,
                             QPushButton, QHBoxLayout, QLineEdit)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QTextCursor, QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QTextCharFormat
from editor_widget import CodeEditor
from scanner import Scanner, Token, TokenType
from parser import Parser, SyntaxError


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


class TokenTable(QTableWidget):
    tokenClicked = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
        
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
        from parser import Parser, SyntaxError
        self.parser = Parser()  
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Compiler")
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
        self.status_label = QLabel("Готов к работе")
        self.status_bar.addWidget(self.status_label)
        
        self.update_status_from_current_tab()
        self.apply_styles()
        
    def create_search_panel(self):
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(10, 5, 10, 5)
        
        search_layout.addWidget(QLabel("Найти:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст или регулярное выражение...")
        self.search_input.setMinimumWidth(300)
        search_layout.addWidget(self.search_input)

        search_layout.addWidget(QLabel("Шаблоны RegExp:"))

        self.regex_presets = QComboBox()
        self.regex_presets.setToolTip("Готовые регулярные выражения для проверки/поиска")
        self.regex_presets.addItem("— выбрать шаблон —", "")
        self.regex_presets.addItem("Франция: номер телефона (моб./стац.)", r"^(?:\+33|0)[1-9](?:[ .-]?\d{2}){4}$")
        self.regex_presets.addItem("snake_case переменная (a-z + _)", r"^[a-z]+(?:_[a-z]+)*$")
        self.regex_presets.addItem(
            "Надёжный пароль (≥14, Рус A/a, цифра, спец)",
            r"^(?=.*[А-ЯЁ])(?=.*[а-яё])(?=.*\d)(?=.*[()#?!|/@/$%\^&*\-_]).{14,}$",
        )
        self.regex_presets.currentIndexChanged.connect(self.on_regex_preset_changed)
        search_layout.addWidget(self.regex_presets)
        
        search_layout.addWidget(QLabel("Тип поиска:"))
        
        self.search_type = QComboBox()
        self.search_type.addItem("Обычный поиск")
        self.search_type.addItem("Регулярное выражение")
        self.search_type.addItem("Целое слово")
        search_layout.addWidget(self.search_type)
        
        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.run_search)
        self.search_button.setFixedWidth(80)
        search_layout.addWidget(self.search_button)
        
        self.search_count_label = QLabel("Найдено: 0")
        self.search_count_label.setFixedWidth(100)
        search_layout.addWidget(self.search_count_label)
        
        search_layout.addStretch()

    def on_regex_preset_changed(self):
        pattern = self.regex_presets.currentData()
        if not pattern:
            return
        self.search_input.setText(pattern)
        # Автоматически включаем режим RegExp
        self.search_type.setCurrentText("Регулярное выражение")
        
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
        
    def create_new_editor_tab(self, file_path=None):
        tab = EditorTab()
        tab.textChanged.connect(self.on_text_changed)
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    tab.set_text(file.read())
                tab.current_file = file_path
                tab_name = os.path.basename(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {str(e)}")
                tab_name = "Новый файл"
        else:
            tab_name = "Новый файл"
        
        index = self.editor_tabs.addTab(tab, tab_name)
        self.editor_tabs.setCurrentIndex(index)
        
        return tab
        
    def close_editor_tab(self, index):
        if self.editor_tabs.count() <= 1:
            QMessageBox.information(self, "Информация", "Нельзя закрыть последнюю вкладку")
            return
            
        tab = self.editor_tabs.widget(index)
        if tab.has_changes():
            reply = QMessageBox.question(
                self, "Сохранение", 
                f"Файл '{self.editor_tabs.tabText(index)}' был изменен. Сохранить изменения?",
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
                font-family: 'Courier New';
                font-size: 11pt;
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
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("Файл")
        
        new_action = QAction("Создать", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Открыть", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("Сохранить", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Сохранить как", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = menubar.addMenu("Правка")
        
        undo_action = QAction("Отмена", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Повтор", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Вырезать", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("Копировать", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("Вставить", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)
        
        delete_action = QAction("Удалить", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_text)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Выделить все", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)
        
        text_menu = menubar.addMenu("Текст")
        
        task_action = QAction("Постановка задачи", self)
        task_action.triggered.connect(self.show_message)
        text_menu.addAction(task_action)
        
        grammar_action = QAction("Грамматика", self)
        grammar_action.triggered.connect(self.show_message)
        text_menu.addAction(grammar_action)
        
        classification_action = QAction("Классификация грамматики", self)
        classification_action.triggered.connect(self.show_message)
        text_menu.addAction(classification_action)
        
        method_action = QAction("Метод анализа", self)
        method_action.triggered.connect(self.show_message)
        text_menu.addAction(method_action)
        
        example_action = QAction("Тестовый пример", self)
        example_action.triggered.connect(self.show_message)
        text_menu.addAction(example_action)
        
        references_action = QAction("Список литературы", self)
        references_action.triggered.connect(self.show_message)
        text_menu.addAction(references_action)
        
        source_action = QAction("Исходный код программы", self)
        source_action.triggered.connect(self.show_message)
        text_menu.addAction(source_action)
        
        run_menu = menubar.addMenu("Пуск")
        run_action = QAction("Запустить анализатор", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_analyzer)
        run_menu.addAction(run_action)
        
        help_menu = menubar.addMenu("Справка")
        
        help_action = QAction("Вызов справки", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("Панель инструментов")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        
        new_action = QAction("Новый", self)
        new_icon = QIcon.fromTheme("document-new")
        if new_icon.isNull():
            new_icon = create_icon("📄")
        new_action.setIcon(new_icon)
        new_action.setToolTip("Создать новый файл (Ctrl+N)")
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Открыть", self)
        open_icon = QIcon.fromTheme("document-open")
        if open_icon.isNull():
            open_icon = create_icon("📂")
        open_action.setIcon(open_icon)
        open_action.setToolTip("Открыть существующий файл (Ctrl+O)")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Сохранить", self)
        save_icon = QIcon.fromTheme("document-save")
        if save_icon.isNull():
            save_icon = create_icon("💾")
        save_action.setIcon(save_icon)
        save_action.setToolTip("Сохранить текущий файл (Ctrl+S)")
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        undo_action = QAction("Отмена", self)
        undo_icon = QIcon.fromTheme("edit-undo")
        if undo_icon.isNull():
            undo_icon = create_icon("↩")
        undo_action.setIcon(undo_icon)
        undo_action.setToolTip("Отменить последнее действие (Ctrl+Z)")
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("Повтор", self)
        redo_icon = QIcon.fromTheme("edit-redo")
        if redo_icon.isNull():
            redo_icon = create_icon("↪")
        redo_action.setIcon(redo_icon)
        redo_action.setToolTip("Повторить отмененное действие (Ctrl+Y)")
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)
        
        toolbar.addSeparator()
        
        copy_action = QAction("Копировать", self)
        copy_icon = QIcon.fromTheme("edit-copy")
        if copy_icon.isNull():
            copy_icon = create_icon("📋")
        copy_action.setIcon(copy_icon)
        copy_action.setToolTip("Копировать выделенный текст (Ctrl+C)")
        copy_action.triggered.connect(self.copy)
        toolbar.addAction(copy_action)
        
        cut_action = QAction("Вырезать", self)
        cut_icon = QIcon.fromTheme("edit-cut")
        if cut_icon.isNull():
            cut_icon = create_icon("✂")
        cut_action.setIcon(cut_icon)
        cut_action.setToolTip("Вырезать выделенный текст (Ctrl+X)")
        cut_action.triggered.connect(self.cut)
        toolbar.addAction(cut_action)
        
        paste_action = QAction("Вставить", self)
        paste_icon = QIcon.fromTheme("edit-paste")
        if paste_icon.isNull():
            paste_icon = create_icon("📌")
        paste_action.setIcon(paste_icon)
        paste_action.setToolTip("Вставить текст из буфера обмена (Ctrl+V)")
        paste_action.triggered.connect(self.paste)
        toolbar.addAction(paste_action)
        
        toolbar.addSeparator()
        
        run_action = QAction("Пуск", self)
        run_icon = QIcon.fromTheme("media-playback-start")
        if run_icon.isNull():
            run_icon = create_icon("▶")
        run_action.setIcon(run_icon)
        run_action.setToolTip("Запустить анализатор (F5)")
        run_action.triggered.connect(self.run_analyzer)
        toolbar.addAction(run_action)
        
        toolbar.addSeparator()
        
        help_action = QAction("Справка", self)
        help_icon = QIcon.fromTheme("help-contents")
        if help_icon.isNull():
            help_icon = create_icon("?")
        help_action.setIcon(help_icon)
        help_action.setToolTip("Вызов справки (F1)")
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
        
        about_action = QAction("О программе", self)
        about_icon = QIcon.fromTheme("help-about")
        if about_icon.isNull():
            about_icon = create_icon("i")
        about_action.setIcon(about_icon)
        about_action.setToolTip("Информация о программе")
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
    
    def new_file(self):
        self.create_new_editor_tab()
        self.status_label.setText("Создан новый файл")
        
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", "", 
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        if file_path:
            self.create_new_editor_tab(file_path)
            self.status_label.setText(f"Открыт файл: {file_path}")
                    
    def save_file(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return False
            
        if tab.current_file:
            try:
                with open(tab.current_file, 'w', encoding='utf-8') as file:
                    file.write(tab.get_text())
                tab.text_changed = False
                self.status_label.setText(f"Файл сохранен: {os.path.basename(tab.current_file)}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
                return False
        else:
            return self.save_file_as()
            
    def save_file_as(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return False
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл как", "", 
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
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
                    self, "Сохранение", 
                    f"Файл '{self.editor_tabs.tabText(i)}' был изменен. Сохранить изменения?",
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel
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
            self.status_label.setText(f"Строка: {line}, Колонка: {col} | Символов: {chars}")
        
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
            tab.highlight_error(line, start_pos, end_pos)
    
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
            QMessageBox.information(self, "Информация", "Нет данных для поиска. Введите текст в редактор.")
            return
        
        self.search_result_table.clear_table()
        tab.clear_highlighting()
        
        search_type = self.search_type.currentText()
        
        results = []
        
        lines = text.split('\n')
        
        try:
            if search_type == "Обычный поиск":
                if not search_pattern:
                    QMessageBox.information(self, "Информация", "Введите текст для поиска")
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
            
            elif search_type == "Регулярное выражение":
                if not search_pattern:
                    QMessageBox.information(self, "Информация", "Введите регулярное выражение")
                    return
                regex = re.compile(search_pattern)
                for line_num, line in enumerate(lines, start=1):
                    for match in regex.finditer(line):
                        start = match.start()
                        end = match.end()
                        results.append((line_num, start + 1, end, match.group()))
            
            elif search_type == "Целое слово":
                if not search_pattern:
                    QMessageBox.information(self, "Информация", "Введите текст для поиска")
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
            self.search_count_label.setText(f"Найдено: {count}")
            
            if count == 0 and search_pattern:
                QMessageBox.information(self, "Результаты поиска", f"Совпадений не найдено для: {search_pattern}")
            elif count > 0:
                self.output_tabs.setCurrentIndex(3)
                self.status_label.setText(f"Поиск завершен. Найдено совпадений: {count}")
                
        except re.error as e:
            QMessageBox.critical(self, "Ошибка", f"Неверное регулярное выражение: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при поиске: {str(e)}")
    
    def run_analyzer(self):
        tab = self.get_current_editor_tab()
        if not tab:
            return
            
        text = tab.get_text()
        if not text.strip():
            QMessageBox.information(self, "Информация", "Введите текст для анализа")
            return
        
        tab.clear_highlighting()
        self.token_table.clear_table()
        self.syntax_error_table.clear_table()
        self.output_area.clear()
        
        try:
            tokens, lex_errors = self.scanner.analyze(text)
            
            for token in tokens:
                self.token_table.add_token(token)
            
            self.output_area.append("=== РЕЗУЛЬТАТЫ ЛЕКСИЧЕСКОГО АНАЛИЗА ===\n")
            self.output_area.append(f"Всего лексем: {len(tokens)}")
            self.output_area.append(f"Лексических ошибок: {len(lex_errors)}\n")
            
            if lex_errors:
                self.output_area.append("=== ЛЕКСИЧЕСКИЕ ОШИБКИ ===")
                for error in lex_errors:
                    self.output_area.append(
                        f"! Строка {error.line}, позиция {error.start_pos}: "
                        f"недопустимый символ '{error.value}'"
                    )
                    self.syntax_error_table.add_error(
                        error.value, error.line, error.start_pos, error.end_pos,
                        f"недопустимый символ '{error.value}'"
                    )
                
                if lex_errors:
                    first = lex_errors[0]
                    self.go_to_position(first.line, first.start_pos)
                    self.output_tabs.setCurrentIndex(2)
                    self.status_label.setText(f"Анализ завершен. Лексических ошибок: {len(lex_errors)}")
                    return
            
            self.output_area.append("\n=== СИНТАКСИЧЕСКИЙ АНАЛИЗ ===\n")
            
            success, syntax_errors = self.parser.analyze(tokens)
            
            if syntax_errors:
                self.output_area.append(f"Найдено синтаксических ошибок: {len(syntax_errors)}\n")
                self.output_area.append("=== СИНТАКСИЧЕСКИЕ ОШИБКИ ===")
                
                for error in syntax_errors:
                    self.output_area.append(
                        f"! '{error.fragment}' | стр.{error.line}, поз.{error.pos} | {error.message}"
                    )
                    if error.fragment == "<конец>":
                        end_pos = error.pos
                    else:
                        end_pos = error.pos + len(error.fragment) - 1
                    self.syntax_error_table.add_error(
                        error.fragment, error.line, error.pos, end_pos, error.message
                    )
                
                if syntax_errors:
                    first = syntax_errors[0]
                    if first.fragment != "<конец>":
                        end_pos = first.pos + len(first.fragment) - 1
                        self.highlight_error(first.line, first.pos, end_pos, 0)
                    else:
                        self.go_to_position(first.line, first.pos)
                    self.output_tabs.setCurrentIndex(2)
            else:
                self.output_area.append("Синтаксических ошибок не обнаружено. Строка корректна.")
            
            total_errors = len(syntax_errors)
            self.status_label.setText(f"Анализ завершен. Всего ошибок: {total_errors}")
            
            if total_errors == 0:
                self.output_area.append("\n✅ Программа синтаксически верна!")
                
        except Exception as e:
            import traceback
            self.output_area.append(f"Ошибка при анализе: {str(e)}")
            self.output_area.append(traceback.format_exc())
            self.status_label.setText("Ошибка при анализе")
    
    def show_message(self):
        sender = self.sender()
        if sender:
            QMessageBox.information(self, sender.text(), 
                                   f"Функция '{sender.text()}' будет реализована позже.")
    
    def show_help(self):
        help_text = """
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
        
        Поиск подстрок:
        
        1. Обычный поиск - поиск точного совпадения строки
        2. Регулярное выражение - поиск по шаблону регулярного выражения
        3. Целое слово - поиск точного совпадения целого слова
        
        Примеры регулярных выражений:
        - \\d+ - поиск чисел
        - [a-zA-Z]+ - поиск слов
        - ^const - поиск строк, начинающихся с const
        - ;$ - поиск строк, заканчивающихся на ;
        """
        
        QMessageBox.information(self, "Справка", help_text)
        
    def show_about(self):
        about_text = "Compiler v4.0\nАвтор: Марков Д.Д.\n2026\n\nДобавлен модуль поиска подстрок с использованием регулярных выражений"
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