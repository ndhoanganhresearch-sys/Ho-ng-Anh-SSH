"""
Integration module for Language Switcher in Tunnel Analysis Window

This module provides helper functions to integrate multilingual support
into the existing TunnelAnalysisWindow.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6 import QtCore, QtWidgets
from translations import get_text, get_all_texts, get_available_languages
from language_switcher import LanguageSwitcher, LanguageSwitcherCompact


class TranslationManager(QtCore.QObject):
    """Manages translations for the entire application."""
    
    language_changed = QtCore.Signal(str)
    
    def __init__(self, initial_language="en"):
        super().__init__()
        self.current_language = initial_language
        self._widgets_to_update = []
        
    def register_widget(self, widget, text_key, attribute="text"):
        """Register a widget to be updated when language changes.
        
        Args:
            widget: The Qt widget to update
            text_key: The translation key
            attribute: The attribute to update (text, windowTitle, toolTip, etc.)
        """
        self._widgets_to_update.append({
            "widget": widget,
            "key": text_key,
            "attribute": attribute
        })
        self._update_widget(widget, text_key, attribute)
        
    def _update_widget(self, widget, text_key, attribute):
        """Update a single widget's text."""
        text = get_text(text_key, self.current_language)
        
        if attribute == "text":
            if hasattr(widget, "setText"):
                widget.setText(text)
        elif attribute == "windowTitle":
            if hasattr(widget, "setWindowTitle"):
                widget.setWindowTitle(text)
        elif attribute == "toolTip":
            if hasattr(widget, "setToolTip"):
                widget.setToolTip(text)
        elif attribute == "placeholderText":
            if hasattr(widget, "setPlaceholderText"):
                widget.setPlaceholderText(text)
                
    def change_language(self, language_code: str):
        """Change the application language and update all registered widgets."""
        if language_code in get_available_languages():
            self.current_language = language_code
            
            # Update all registered widgets
            for item in self._widgets_to_update:
                widget = item["widget"]
                if widget and not widget.isHidden():  # Only update visible widgets
                    self._update_widget(widget, item["key"], item["attribute"])
            
            self.language_changed.emit(language_code)
            
    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.current_language
        
    def t(self, key: str) -> str:
        """Shorthand for get_text with current language."""
        return get_text(key, self.current_language)


def create_language_toolbar(parent=None, translation_manager=None, style="dropdown"):
    """Create a language switcher toolbar widget.
    
    Args:
        parent: Parent widget
        translation_manager: TranslationManager instance
        style: "dropdown" or "compact"
        
    Returns:
        QWidget containing the language switcher
    """
    toolbar = QtWidgets.QWidget(parent)
    layout = QtWidgets.QHBoxLayout(toolbar)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    
    # Label
    label = QtWidgets.QLabel("🌐")
    label.setStyleSheet("font-size: 12pt; color: #64748B;")
    layout.addWidget(label)
    
    # Switcher
    if style == "compact":
        switcher = LanguageSwitcherCompact(toolbar)
    else:
        switcher = LanguageSwitcher(toolbar)
    
    layout.addWidget(switcher, 1)
    
    # Connect to translation manager if provided
    if translation_manager:
        switcher.language_changed.connect(translation_manager.change_language)
        switcher.set_language(translation_manager.get_current_language())
    
    return toolbar, switcher


def add_language_switcher_to_sidebar(sidebar_layout, translation_manager=None, position=0):
    """Add language switcher to an existing sidebar layout.
    
    Args:
        sidebar_layout: QVBoxLayout of the sidebar
        translation_manager: TranslationManager instance
        position: Position to insert (0 = top, -1 = bottom)
        
    Returns:
        The language switcher widget
    """
    # Create language switcher frame
    lang_frame = QtWidgets.QFrame()
    lang_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #F8FAFC, stop:1 #F1F5F9);
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 8px;
        }
    """)
    
    lang_layout = QtWidgets.QVBoxLayout(lang_frame)
    lang_layout.setContentsMargins(8, 8, 8, 8)
    lang_layout.setSpacing(6)
    
    # Title
    title = QtWidgets.QLabel("Language / 언어 / Ngôn ngữ")
    title.setStyleSheet("font-size: 9pt; font-weight: 600; color: #475569; background: transparent; border: none;")
    lang_layout.addWidget(title)
    
    # Switcher
    switcher = LanguageSwitcherCompact()
    lang_layout.addWidget(switcher)
    
    # Connect to translation manager
    if translation_manager:
        switcher.language_changed.connect(translation_manager.change_language)
        switcher.set_language(translation_manager.get_current_language())
    
    # Insert into sidebar
    if position == -1:
        sidebar_layout.addWidget(lang_frame)
    else:
        sidebar_layout.insertWidget(position, lang_frame)
    
    return switcher


# Demo application
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Create translation manager
    tm = TranslationManager(initial_language="en")
    
    # Create demo window
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Translation Manager Demo")
    window.resize(600, 400)
    
    # Central widget
    central = QtWidgets.QWidget()
    window.setCentralWidget(central)
    layout = QtWidgets.QVBoxLayout(central)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)
    
    # Title
    title = QtWidgets.QLabel()
    title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1E293B;")
    tm.register_widget(title, "window_title", "text")
    layout.addWidget(title)
    
    # Language toolbar
    toolbar, switcher = create_language_toolbar(central, tm, style="compact")
    layout.addWidget(toolbar)
    
    layout.addSpacing(20)
    
    # Sample buttons
    btn1 = QtWidgets.QPushButton()
    tm.register_widget(btn1, "import_btn", "text")
    layout.addWidget(btn1)
    
    btn2 = QtWidgets.QPushButton()
    tm.register_widget(btn2, "register_btn", "text")
    layout.addWidget(btn2)
    
    btn3 = QtWidgets.QPushButton()
    tm.register_widget(btn3, "deformation_btn", "text")
    layout.addWidget(btn3)
    
    layout.addStretch()
    
    # Status label
    status = QtWidgets.QLabel()
    status.setStyleSheet("color: #64748B; font-size: 9pt;")
    
    def update_status(lang):
        status.setText(f"Current language: {lang}")
    
    tm.language_changed.connect(update_status)
    update_status(tm.get_current_language())
    layout.addWidget(status)
    
    window.show()
    sys.exit(app.exec())
