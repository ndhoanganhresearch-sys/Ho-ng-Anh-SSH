import sys
import threading
import time
from PySide6 import QtCore, QtGui, QtWidgets

# Create minimal QApplication
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

callback_called = False

def main_thread_callback():
    global callback_called
    callback_called = True
    print('Callback executed in main thread')

def background_thread():
    print(f'Background thread ID: {threading.get_ident()}')
    try:
        QtCore.QTimer.singleShot(100, main_thread_callback)
        print('QTimer.singleShot succeeded from background thread')
    except Exception as e:
        print(f'QTimer.singleShot raised: {type(e).__name__}: {e}')

print(f'Main thread ID: {threading.get_ident()}')
t = threading.Thread(target=background_thread, daemon=True)
t.start()
t.join(timeout=5)

for _ in range(100):
    app.processEvents()
    if callback_called:
        print('Callback was executed')
        break
    time.sleep(0.01)

if not callback_called:
    print('Callback was NOT executed')
