"""
Patch to add multilingual support to Tunnel Analysis Window

This file demonstrates how to integrate the language switcher into the existing application.
Add this code to tunnel_analysis/ui/main_window.py
"""

# Add these imports at the top of main_window.py (after existing imports)
INTEGRATION_CODE = '''
# Multilingual support imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from translations import get_text, get_all_texts
from language_switcher import LanguageSwitcherCompact
from translation_manager import TranslationManager
'''

# Add this to __init__ method of TunnelAnalysisWindow (after self.context initialization)
INIT_CODE = '''
        # Initialize translation manager
        self.translation_manager = TranslationManager(initial_language="en")
        self.current_language = "en"
'''

# Add this method to TunnelAnalysisWindow class
METHOD_CODE = '''
    def _create_language_switcher(self) -> QtWidgets.QFrame:
        """Create language switcher widget for sidebar."""
        lang_frame = QtWidgets.QFrame()
        lang_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8FAFC, stop:1 #F1F5F9);
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        
        lang_layout = QtWidgets.QVBoxLayout(lang_frame)
        lang_layout.setContentsMargins(8, 8, 8, 8)
        lang_layout.setSpacing(6)
        
        # Title
        title = QtWidgets.QLabel("🌐 Language / 언어 / Ngôn ngữ")
        title.setStyleSheet("""
            font-size: 9pt; 
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
    
    def _on_language_changed(self, language_code: str):
        """Handle language change event."""
        self.current_language = language_code
        self.translation_manager.change_language(language_code)
        
        # Update window title
        titles = {
            "en": "Tunnel Analysis v4.0 (r1) - CBNU Smart Structure Lab",
            "vi": "Phân Tích Hầm v4.0 (r1) - Phòng Thí Nghiệm Kết Cấu Thông Minh CBNU",
            "ko": "터널 분석 v4.0 (r1) - CBNU 스마트 구조 연구실"
        }
        self.setWindowTitle(titles.get(language_code, titles["en"]))
        
        # Refresh UI elements
        self._refresh_ui_texts()
        
        # Show notification
        QtWidgets.QMessageBox.information(
            self,
            "Language Changed" if language_code == "en" else 
            "Ngôn ngữ đã thay đổi" if language_code == "vi" else "언어 변경됨",
            f"Language changed to: {language_code.upper()}"
        )
    
    def _refresh_ui_texts(self):
        """Refresh all UI text elements after language change."""
        # This method should update all visible text in the UI
        # based on self.current_language
        
        # Example: Update tab names
        tab_keys = [
            "tab_overview", "tab_registration", "tab_ransac", "tab_centerline",
            "tab_section", "tab_rings", "tab_timeseries", "tab_frenet",
            "tab_heatmap", "tab_results", "tab_ai_chat"
        ]
        
        # Update right tabs if they exist
        if hasattr(self, 'right_tabs'):
            for i in range(self.right_tabs.count()):
                if i < len(tab_keys):
                    text = get_text(tab_keys[i], self.current_language)
                    self.right_tabs.setTabText(i, text)
        
        # Force repaint
        self.update()
'''

# Modification to _build_sidebar method
SIDEBAR_MODIFICATION = '''
    # In _build_sidebar method, add this after the title section (after sep.addWidget(sep)):
    
    # Add language switcher at the top of sidebar
    out.addWidget(self._create_language_switcher())
    out.addSpacing(8)
'''

print("=" * 80)
print("MULTILINGUAL INTEGRATION GUIDE FOR TUNNEL ANALYSIS")
print("=" * 80)
print()
print("Step 1: Add imports to tunnel_analysis/ui/main_window.py")
print("-" * 80)
print(INTEGRATION_CODE)
print()
print("Step 2: Add to __init__ method")
print("-" * 80)
print(INIT_CODE)
print()
print("Step 3: Add these methods to TunnelAnalysisWindow class")
print("-" * 80)
print(METHOD_CODE)
print()
print("Step 4: Modify _build_sidebar method")
print("-" * 80)
print(SIDEBAR_MODIFICATION)
print()
print("=" * 80)
print("INTEGRATION COMPLETE!")
print("=" * 80)
