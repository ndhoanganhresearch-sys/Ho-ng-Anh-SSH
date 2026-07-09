"""
Test to verify QThread.quit() behavior with blocking callbacks.
This tests the claim that quit() doesn't work when run() is blocking.
"""
import sys
import time
from PySide6 import QtCore, QtWidgets

class TestWorker(QtCore.QObject):
    finished = QtCore.Signal()

    def __init__(self, duration_sec):
        super().__init__()
        self.duration_sec = duration_sec
        self.completed = False

    @QtCore.Slot()
    def run(self):
        """Blocking callback that takes time."""
        print(f"Worker: Starting blocking task for {self.duration_sec}s...")
        start = time.time()
        while time.time() - start < self.duration_sec:
            time.sleep(0.1)
        print(f"Worker: Blocking task completed after {time.time() - start:.1f}s")
        self.completed = True
        self.finished.emit()

def test_qthread_quit_with_blocking_callback():
    """Test if quit()/wait() works with a blocking callback."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    print("\n=== Test 1: Normal completion (callback finishes before quit) ===")
    worker1 = TestWorker(duration_sec=0.5)
    thread1 = QtCore.QThread()
    worker1.moveToThread(thread1)
    thread1.started.connect(worker1.run)
    worker1.finished.connect(thread1.quit)
    thread1.start()

    # Wait for thread to finish naturally
    result1 = thread1.wait(5000)
    print(f"Thread1.wait(5000) returned: {result1} (True=thread stopped, False=timeout)")
    print(f"Worker1 completed: {worker1.completed}")

    print("\n=== Test 2: quit() called while callback is running ===")
    worker2 = TestWorker(duration_sec=3.0)
    thread2 = QtCore.QThread()
    worker2.moveToThread(thread2)
    thread2.started.connect(worker2.run)
    thread2.start()

    # Give worker a moment to start
    time.sleep(0.2)

    # Try to quit while callback is still running
    print(f"Calling quit() while callback is running...")
    thread2.quit()
    result2 = thread2.wait(1000)  # Wait only 1 second (callback needs 3s)
    print(f"Thread2.wait(1000) returned: {result2} (should be False=timeout if quit doesn't work)")
    print(f"Worker2 completed: {worker2.completed}")

    # Check if thread actually stopped
    print(f"Thread2.isRunning(): {thread2.isRunning()}")

    # Force cleanup
    if thread2.isRunning():
        thread2.wait(5000)

    print("\n=== Summary ===")
    print("If Test 2 shows wait()=False but callback completes, quit() didn't interrupt the callback.")
    print("If Test 2 shows wait()=True, quit() worked as expected.")

if __name__ == "__main__":
    test_qthread_quit_with_blocking_callback()
