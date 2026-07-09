import sys
import threading
import time
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

class TestWidget(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.text_edit = QtWidgets.QPlainTextEdit()
        self.setCentralWidget(self.text_edit)
        self.setWindowTitle('Test')

widget = TestWidget()

def log_from_background(msg):
    # This should be called from main thread via QTimer
    print(f'log_from_background called from thread {threading.get_ident()}')
    widget.text_edit.appendPlainText(msg)

def background_thread():
    main_thread_id = threading.main_thread().ident
    print(f'Background thread ID: {threading.get_ident()}, Main thread: {main_thread_id}')
    
    msg = 'Message from background'
    print(f'Calling QTimer.singleShot to invoke callback...')
    
    try:
        QtCore.QTimer.singleShot(200, lambda: log_from_background(f'[RAG] {msg}'))
        print('QTimer.singleShot call succeeded')
    except Exception as e:
        print(f'Exception: {type(e).__name__}: {e}')

print(f'Main thread ID: {threading.get_ident()}')
print('Starting background thread...')
t = threading.Thread(target=background_thread, daemon=True)
t.start()

print('Processing events for 2 seconds...')
start = time.time()
while time.time() - start < 2:
    app.processEvents()
    time.sleep(0.01)

print(f'Text in widget: {repr(widget.text_edit.toPlainText())}')
