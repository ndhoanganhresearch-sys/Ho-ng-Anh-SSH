import sys
import threading
import time
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

class MyObject(QtCore.QObject):
    def __init__(self):
        super().__init__()
        print(f'MyObject created in thread: {threading.get_ident()}')

my_obj = MyObject()

def background_thread():
    print(f'Background thread ID: {threading.get_ident()}')
    try:
        # Try to create a child QObject from background thread
        child = QtCore.QObject(my_obj)
        print('Created child QObject without exception')
    except Exception as e:
        print(f'Exception when creating child: {type(e).__name__}: {e}')
    
    try:
        # Try QTimer.singleShot
        QtCore.QTimer.singleShot(100, lambda: print('Timer fired'))
        print('QTimer.singleShot succeeded')
    except Exception as e:
        print(f'Exception in QTimer: {type(e).__name__}: {e}')

print(f'Main thread ID: {threading.get_ident()}')
t = threading.Thread(target=background_thread, daemon=True)
t.start()
t.join(timeout=2)

for _ in range(100):
    app.processEvents()
    time.sleep(0.01)
