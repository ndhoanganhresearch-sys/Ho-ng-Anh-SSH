"""
Tunnel Analysis Multilingual Demo Application

This is a simplified demo showing how the language switcher works
with the tunnel analysis interface.
"""

import sys
from PySide6 import QtCore, QtGui, QtWidgets
from translations import get_text, get_all_texts, get_available_languages
from language_switcher import LanguageSwitcherCompact
from translation_manager import TranslationManager


class TunnelAnalysisDemoWindow(QtWidgets.QMainWindow):
    """Demo window showing multilingual tunnel analysis interface."""
    
    def __init__(self):
        super().__init__()
        self.translation_manager = TranslationManager(initial_language="en")
        self.current_language = "en"
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Tunnel Analysis v4.0 - Multilingual Demo")
        self.resize(1200, 800)
        
        # Central widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add sidebar
        main_layout.addWidget(self._create_sidebar())
        
        # Add main content area
        main_layout.addWidget(self._create_content_area(), 1)
        
    def _create_sidebar(self) -> QtWidgets.QFrame:
        """Create the sidebar with language switcher."""
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(350)
        sidebar.setStyleSheet("""
            QFrame {
                background: #F8FAFC;
                border-right: 2px solid #CBD5E1;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(12)
        
        # Title
        title = QtWidgets.QLabel("TUNNEL ANALYSIS")
        title.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            color: #0F172A;
            padding: 8px;
        """)
        layout.addWidget(title)
        
        subtitle = QtWidgets.QLabel("v4.0 - CBNU Smart Structure Lab")
        subtitle.setStyleSheet("""
            font-size: 9pt;
            color: #64748B;
            padding: 0px 8px 8px 8px;
        """)
        layout.addWidget(subtitle)
        
        # Separator
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet("background: #CBD5E1; max-height: 1px;")
        layout.addWidget(sep)
        
        # Language switcher
        layout.addWidget(self._create_language_switcher())
        
        layout.addSpacing(12)
        
        # Sample buttons
        self._create_sample_buttons(layout)
        
        layout.addStretch()
        
        # Status
        self.status_label = QtWidgets.QLabel()
        self.status_label.setStyleSheet("""
            font-size: 8pt;
            color: #94A3B8;
            padding: 8px;
            background: #F1F5F9;
            border-radius: 4px;
        """)
        self.translation_manager.register_widget(self.status_label, "ready_status", "text")
        layout.addWidget(self.status_label)
        
        return sidebar
        
    def _create_language_switcher(self) -> QtWidgets.QFrame:
        """Create language switcher widget."""
        lang_frame = QtWidgets.QFrame()
        lang_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8FAFC);
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        lang_layout = QtWidgets.QVBoxLayout(lang_frame)
        lang_layout.setContentsMargins(10, 10, 10, 10)
        lang_layout.setSpacing(8)
        
        # Title
        title = QtWidgets.QLabel("🌐 Language / 언어 / Ngôn ngữ")
        title.setStyleSheet("""
            font-size: 9.5pt;
            font-weight: 600;
            color: #475569;
            background: transparent;
            border: none;
        """)
        lang_layout.addWidget(title)
        
        # Language switcher
        self.language_switcher = LanguageSwitcherCompact()
        self.language_switcher.language_changed.connect(self._on_language_changed)
        lang_layout.addWidget(self.language_switcher)
        
        return lang_frame
        
    def _create_sample_buttons(self, layout):
        """Create sample buttons to demonstrate translation."""
        buttons_data = [
            ("import_btn", "#1D4ED8"),
            ("register_btn", "#059669"),
            ("deformation_btn", "#DC2626"),
        ]
        
        self.sample_buttons = []
        
        for key, color in buttons_data:
            btn = QtWidgets.QPushButton()
            btn.setMinimumHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 10pt;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {color}DD;
                }}
            """)
            self.translation_manager.register_widget(btn, key, "text")
            layout.addWidget(btn)
            self.sample_buttons.append(btn)
            
    def _create_content_area(self) -> QtWidgets.QWidget:
        """Create main content area with tabs."""
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QtWidgets.QLabel()
        header.setStyleSheet("""
            font-size: 18pt;
            font-weight: bold;
            color: #0F172A;
            padding: 12px;
        """)
        self.translation_manager.register_widget(header, "window_title", "text")
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background: white;
            }
            QTabBar::tab {
                background: #F1F5F9;
                color: #475569;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1D4ED8;
            }
            QTabBar::tab:hover {
                background: #E2E8F0;
            }
        """)
        
        # Create tabs
        tab_keys = [
            "tab_overview",
            "tab_registration",
            "tab_centerline",
            "tab_heatmap",
            "tab_results",
        ]
        
        self.tab_widgets = []
        for key in tab_keys:
            tab_widget = QtWidgets.QWidget()
            tab_layout = QtWidgets.QVBoxLayout(tab_widget)
            
            label = QtWidgets.QLabel()
            label.setStyleSheet("font-size: 11pt; color: #64748B; padding: 20px;")
            self.translation_manager.register_widget(label, key + "_label", "text")
            tab_layout.addWidget(label)
            tab_layout.addStretch()
            
            self.tabs.addTab(tab_widget, "")
            self.tab_widgets.append((self.tabs, len(self.tab_widgets), key))
        
        layout.addWidget(self.tabs)
        
        return content
        
    def _on_language_changed(self, language_code: str):
        """Handle language change event."""
        self.current_language = language_code
        self.translation_manager.change_language(language_code)
        
        # Update window title
        titles = {
            "en": "Tunnel Analysis v4.0 - Multilingual Demo",
            "vi": "Phân Tích Hầm v4.0 - Demo Đa Ngôn Ngữ",
            "ko": "터널 분석 v4.0 - 다국어 데모"
        }
        self.setWindowTitle(titles.get(language_code, titles["en"]))
        
        # Update tab titles
        for tab_widget, index, key in self.tab_widgets:
            text = get_text(key, language_code)
            self.tabs.setTabText(index, text)
        
        # Show notification
        messages = {
            "en": f"Language changed to English",
            "vi": f"Đã chuyển sang Tiếng Việt",
            "ko": f"한국어로 변경되었습니다"
        }
        
        QtWidgets.QMessageBox.information(
            self,
            "Language Changed" if language_code == "en" else 
            "Ngôn ngữ đã thay đổi" if language_code == "vi" else "언어 변경",
            messages.get(language_code, messages["en"])
        )


def main():
    """Run the demo application."""
    app = QtWidgets.QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show window
    window = TunnelAnalysisDemoWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
