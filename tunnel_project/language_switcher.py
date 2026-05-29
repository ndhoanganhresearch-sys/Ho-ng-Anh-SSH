"""
Language Switcher Widget for SSL Tunnel Monitoring System

This module provides a professional language switcher widget with dropdown menu.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from translations import get_available_languages, get_language_name, get_language_flag, LANGUAGE_INFO


class LanguageSwitcher(QtWidgets.QPushButton):
    """Professional language switcher button with dropdown menu."""
    
    language_changed = QtCore.Signal(str)  # Emits language code when changed
    
    def __init__(self, parent=None, initial_language="en"):
        super().__init__(parent)
        self.current_language = initial_language
        self._setup_ui()
        self._create_menu()
        
    def _setup_ui(self):
        """Setup the button appearance."""
        self.setFixedHeight(36)
        self.setMinimumWidth(140)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._update_button_text()
        
        # Professional styling
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8FAFC);
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 12px;
                text-align: left;
                font-size: 10pt;
                font-weight: 600;
                color: #1E293B;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8FAFC, stop:1 #F1F5F9);
                border: 1px solid #94A3B8;
            }
            QPushButton:pressed {
                background: #E2E8F0;
                border: 1px solid #64748B;
            }
            QPushButton::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                right: 8px;
                width: 12px;
            }
        """)
        
    def _create_menu(self):
        """Create dropdown menu with all available languages."""
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px;
                font-size: 10pt;
            }
            QMenu::item {
                padding: 8px 24px 8px 12px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background: #DBEAFE;
                color: #1E40AF;
            }
            QMenu::item:disabled {
                color: #94A3B8;
            }
            QMenu::separator {
                height: 1px;
                background: #E2E8F0;
                margin: 4px 8px;
            }
        """)
        
        # Add language options
        for lang_code in get_available_languages():
            flag = get_language_flag(lang_code)
            name = get_language_name(lang_code)
            
            action = QtGui.QAction(f"{flag}  {name}", self)
            action.setData(lang_code)
            
            # Mark current language
            if lang_code == self.current_language:
                action.setCheckable(True)
                action.setChecked(True)
                font = action.font()
                font.setBold(True)
                action.setFont(font)
            
            action.triggered.connect(lambda checked=False, code=lang_code: self._on_language_selected(code))
            menu.addAction(action)
        
        self.setMenu(menu)
        
    def _update_button_text(self):
        """Update button text with current language."""
        flag = get_language_flag(self.current_language)
        name = get_language_name(self.current_language)
        self.setText(f"{flag}  {name}")
        
    def _on_language_selected(self, language_code: str):
        """Handle language selection."""
        if language_code != self.current_language:
            self.current_language = language_code
            self._update_button_text()
            self._create_menu()  # Recreate menu to update checkmarks
            self.language_changed.emit(language_code)
            
    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.current_language
        
    def set_language(self, language_code: str):
        """Programmatically set the language."""
        if language_code in get_available_languages():
            self._on_language_selected(language_code)


class LanguageSwitcherCompact(QtWidgets.QComboBox):
    """Compact language switcher using QComboBox."""
    
    language_changed = QtCore.Signal(str)
    
    def __init__(self, parent=None, initial_language="en"):
        super().__init__(parent)
        self.current_language = initial_language
        self._setup_ui()
        self._populate_languages()
        
    def _setup_ui(self):
        """Setup the combobox appearance."""
        self.setFixedHeight(32)
        self.setMinimumWidth(130)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        self.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 4px 8px;
                font-size: 9.5pt;
                font-weight: 600;
                color: #1E293B;
            }
            QComboBox:hover {
                border: 1px solid #94A3B8;
                background: #F8FAFC;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #64748B;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
                selection-background-color: #DBEAFE;
                selection-color: #1E40AF;
                font-size: 9.5pt;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 12px;
                border-radius: 4px;
                margin: 2px;
            }
        """)
        
        self.currentIndexChanged.connect(self._on_selection_changed)
        
    def _populate_languages(self):
        """Populate combobox with languages."""
        self.blockSignals(True)
        self.clear()
        
        for lang_code in get_available_languages():
            flag = get_language_flag(lang_code)
            name = get_language_name(lang_code)
            self.addItem(f"{flag}  {name}", lang_code)
            
            if lang_code == self.current_language:
                self.setCurrentIndex(self.count() - 1)
        
        self.blockSignals(False)
        
    def _on_selection_changed(self, index: int):
        """Handle selection change."""
        if index >= 0:
            language_code = self.itemData(index)
            if language_code and language_code != self.current_language:
                self.current_language = language_code
                self.language_changed.emit(language_code)
                
    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.current_language
        
    def set_language(self, language_code: str):
        """Programmatically set the language."""
        for i in range(self.count()):
            if self.itemData(i) == language_code:
                self.setCurrentIndex(i)
                break


# Demo application
if __name__ == "__main__":
    import sys
    
    app = QtWidgets.QApplication(sys.argv)
    
    # Create demo window
    window = QtWidgets.QWidget()
    window.setWindowTitle("Language Switcher Demo")
    window.resize(400, 300)
    
    layout = QtWidgets.QVBoxLayout(window)
    layout.setSpacing(20)
    layout.setContentsMargins(30, 30, 30, 30)
    
    # Title
    title = QtWidgets.QLabel("SSL Tunnel Monitoring System")
    title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1E293B;")
    layout.addWidget(title)
    
    # Dropdown style switcher
    layout.addWidget(QtWidgets.QLabel("Dropdown Style:"))
    switcher1 = LanguageSwitcher()
    switcher1.language_changed.connect(lambda lang: print(f"Language changed to: {lang}"))
    layout.addWidget(switcher1)
    
    layout.addSpacing(20)
    
    # Compact style switcher
    layout.addWidget(QtWidgets.QLabel("Compact Style:"))
    switcher2 = LanguageSwitcherCompact()
    switcher2.language_changed.connect(lambda lang: print(f"Compact switcher changed to: {lang}"))
    layout.addWidget(switcher2)
    
    # Sync both switchers
    switcher1.language_changed.connect(switcher2.set_language)
    switcher2.language_changed.connect(switcher1.set_language)
    
    layout.addStretch()
    
    # Current language display
    current_label = QtWidgets.QLabel(f"Current: {switcher1.get_current_language()}")
    current_label.setStyleSheet("color: #64748B; font-size: 9pt;")
    layout.addWidget(current_label)
    
    def update_current_label(lang):
        current_label.setText(f"Current: {lang}")
    
    switcher1.language_changed.connect(update_current_label)
    
    window.show()
    sys.exit(app.exec())
