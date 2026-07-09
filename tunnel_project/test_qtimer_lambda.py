import sys
import threading
import time
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

results = []

def on_timer(msg):
    results.append(msg)
    print(f'Timer fired with: {msg}')

def background_thread():
    msg = 'Test message from background'
    print(f'Background thread calling QTimer.singleShot with msg: {msg}')
    try:
        # Using lambda like the real code
        QtCore.QTimer.singleShot(100, lambda: on_timer(f'[RAG] {msg}'))
        print('QTimer.singleShot returned without exception')
    except Exception as e:
        print(f'Exception: {e}')

print('Starting test...')
t = threading.Thread(target=background_thread, daemon=True)
t.start()
t.join(timeout=2)

print('Processing events for 1 second...')
for _ in range(100):
    app.processEvents()
    time.sleep(0.01)

print(f'Results collected: {results}')
print(f'Test result: {"PASS - callback was called" if results else "FAIL - callback was NOT called"}')
