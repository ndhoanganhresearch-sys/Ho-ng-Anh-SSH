#!/usr/bin/env python
"""Test if QTimer.singleShot callback is actually invoked from a daemon thread."""
from PySide6 import QtCore, QtWidgets
import threading
import time
import sys

print("=== Real-world test: can a daemon thread call QTimer.singleShot? ===\n")

# Simulate the main_window.py scenario
class FakeMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.log_messages = []
        # Simulate results_text
        self.results_text = QtWidgets.QPlainTextEdit()
        self.setCentralWidget(self.results_text)

        print("[MAIN] Starting daemon thread to initialize RAG (simulated)...")
        threading.Thread(target=self._init_rag_sim, daemon=True).start()

        # Process events for a bit to let the thread run
        for _ in range(20):
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.05)

    def _init_rag_sim(self):
        """Simulates TunnelRAGAssistant initialization in daemon thread"""
        msg = "[RAG] Model loaded successfully"
        print(f"[WORKER] About to call QTimer.singleShot from daemon thread...")
        try:
            QtCore.QTimer.singleShot(500, lambda: self._log(f"{msg}"))
            print(f"[WORKER] QTimer.singleShot call succeeded (no exception)")
        except Exception as e:
            print(f"[WORKER] QTimer.singleShot call FAILED: {e}")

    def _log(self, msg: str) -> None:
        """Append to results text widget"""
        self.results_text.appendPlainText(str(msg))
        self.log_messages.append(msg)
        print(f"[MAIN] _log called with: {msg}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = FakeMainWindow()
    window.setWindowTitle("QTimer.singleShot Test")
    window.resize(600, 400)
    window.show()

    # Run event loop
    print("\n[MAIN] Running event loop for 3 seconds...")
    QtCore.QTimer.singleShot(3000, app.quit)
    app.exec()

    print(f"\n[MAIN] Final result: log_messages = {window.log_messages}")
    if window.log_messages:
        print("SUCCESS: Timer callback WAS invoked from daemon thread!")
    else:
        print("NOTE: Timer callback was NOT invoked (but no exception either)")
