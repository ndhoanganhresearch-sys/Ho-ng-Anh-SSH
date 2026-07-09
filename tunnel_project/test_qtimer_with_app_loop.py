#!/usr/bin/env python
"""Test QTimer.singleShot with actual QApplication.exec() running."""
import sys
import threading
import time
from PySide6 import QtCore, QtGui, QtWidgets

class TestWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.callback_called = False
        self.setWindowTitle("QTimer Test")
        label = QtWidgets.QLabel("Check console for results")
        self.setCentralWidget(label)

        # Start background thread
        t = threading.Thread(target=self._background_thread, daemon=True)
        t.start()

        # Quit after 2 seconds
        QtCore.QTimer.singleShot(2000, QtWidgets.QApplication.quit)

    def _background_thread(self):
        print(f"Background thread ID: {threading.get_ident()}")
        try:
            # This is what the buggy code does
            QtCore.QTimer.singleShot(100, self._callback)
            print("QTimer.singleShot succeeded from background thread")
        except Exception as e:
            print(f"QTimer.singleShot raised: {type(e).__name__}: {e}")

    def _callback(self):
        self.callback_called = True
        print("Callback executed in main thread!")

if __name__ == "__main__":
    print(f"Main thread ID: {threading.get_ident()}")
    app = QtWidgets.QApplication(sys.argv)
    window = TestWindow()
    window.show()

    # Run the event loop - this is key!
    app.exec()

    print(f"Callback was {'executed' if window.callback_called else 'NOT executed'}")
