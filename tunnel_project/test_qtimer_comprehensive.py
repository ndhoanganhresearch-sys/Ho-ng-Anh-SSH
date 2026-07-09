#!/usr/bin/env python
"""Comprehensive test: QTimer.singleShot behavior from background thread."""
import sys
import threading
import time
import io
from contextlib import redirect_stderr
from PySide6 import QtCore, QtGui, QtWidgets

print("=" * 70)
print("COMPREHENSIVE QTIMER.SINGLESSHOT TEST")
print("=" * 70)

class TestWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QTimer Test")
        self.callback_count = 0
        self.log_messages = []

        # Create a text edit like main_window does
        self.results_text = QtWidgets.QPlainTextEdit()
        self.results_text.setReadOnly(True)
        self.setCentralWidget(self.results_text)

        print("\n[INIT] Window created, starting background thread...")
        # Simulate the exact code from main_window.py line 88-89
        threading.Thread(target=self._init_rag, daemon=True).start()

        # Quit after 2 seconds
        QtCore.QTimer.singleShot(2000, QtWidgets.QApplication.quit)

    def _init_rag(self):
        """Exact simulation of main_window._init_rag()"""
        msg = "[RAG] Model initialized"
        print(f"[BACKGROUND] _init_rag running on daemon thread (ID: {threading.get_ident()})")
        try:
            # This is the exact code from main_window.py line 1680
            QtCore.QTimer.singleShot(500, lambda: self._log(f"[RAG] {msg}"))
            print(f"[BACKGROUND] QTimer.singleShot succeeded (no exception)")
        except Exception as e:
            print(f"[BACKGROUND] QTimer.singleShot FAILED: {type(e).__name__}: {e}")

    def _log(self, msg: str):
        """Exact code from main_window.py line 3779"""
        self.callback_count += 1
        self.results_text.appendPlainText(str(msg))
        self.log_messages.append(msg)
        print(f"[MAIN THREAD] _log called: {msg}")

if __name__ == "__main__":
    print(f"\nMain thread ID: {threading.get_ident()}\n")

    # Capture any Qt warnings to stderr
    stderr_capture = io.StringIO()

    app = QtWidgets.QApplication(sys.argv)
    window = TestWindow()
    window.show()

    print("[MAIN] Running QApplication.exec()...\n")

    # Run the event loop
    with redirect_stderr(stderr_capture):
        app.exec()

    print(f"\n[RESULT] Callback was called {window.callback_count} time(s)")
    print(f"[RESULT] Log messages: {window.log_messages}")

    stderr_output = stderr_capture.getvalue()
    if stderr_output:
        print(f"\n[WARNINGS/ERRORS from Qt]:\n{stderr_output}")
    else:
        print("\n[WARNINGS/ERRORS from Qt]: None")

    print("\n" + "=" * 70)
    if window.callback_count == 0:
        print("CONCLUSION: QTimer.singleShot from daemon thread DOES NOT FIRE")
        print("VERDICT: Not a memory leak or crash, just a silent no-op")
    else:
        print("CONCLUSION: QTimer.singleShot from daemon thread DID FIRE")
        print("VERDICT: Thread-safe, callback executed successfully")
    print("=" * 70)
