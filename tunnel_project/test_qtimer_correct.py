#!/usr/bin/env python
"""Test the CORRECT way to call Qt methods from a background thread."""
import sys
import threading
import time
from PySide6 import QtCore, QtGui, QtWidgets

class TestWindow(QtWidgets.QMainWindow):
    # Signal for thread-safe communication
    log_signal = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.callback_called = False
        self.setWindowTitle("QTimer Test - Correct Way")
        label = QtWidgets.QLabel("Check console for results")
        self.setCentralWidget(label)

        # Connect signal to slot (thread-safe)
        self.log_signal.connect(self._on_log)

        # Start background thread
        t = threading.Thread(target=self._background_thread, daemon=True)
        t.start()

        # Quit after 2 seconds
        QtCore.QTimer.singleShot(2000, QtWidgets.QApplication.quit)

    def _background_thread(self):
        print(f"Background thread ID: {threading.get_ident()}")
        try:
            # CORRECT WAY: Use Qt.QueuedConnection (via Signal.emit)
            self.log_signal.emit("Timer emitted from background thread")
            print("Signal.emit succeeded from background thread")
        except Exception as e:
            print(f"Signal.emit raised: {type(e).__name__}: {e}")

    def _on_log(self, msg: str):
        self.callback_called = True
        print(f"Slot executed in main thread: {msg}")

    # Now test the BUGGY way that was claimed in the issue
    def _test_buggy_way(self):
        """This is what main_window.py does"""
        t = threading.Thread(target=self._buggy_background, daemon=True)
        t.start()

    def _buggy_background(self):
        print(f"\nBuggy approach - Background thread ID: {threading.get_ident()}")
        try:
            # This is the allegedly buggy code
            QtCore.QTimer.singleShot(500, lambda: self._callback())
            print("QTimer.singleShot succeeded from background thread")
        except Exception as e:
            print(f"QTimer.singleShot raised: {type(e).__name__}: {e}")

    def _callback(self):
        print("_callback executed in main thread!")

if __name__ == "__main__":
    print(f"Main thread ID: {threading.get_ident()}")
    app = QtWidgets.QApplication(sys.argv)
    window = TestWindow()
    window.show()

    # Test buggy approach after a delay
    QtCore.QTimer.singleShot(500, window._test_buggy_way)

    # Run the event loop
    app.exec()

    print(f"\nSignal-based callback was {'executed' if window.callback_called else 'NOT executed'}")
