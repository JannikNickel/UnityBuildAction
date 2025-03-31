import time
import fcntl
import atexit
import signal
from log import *

class LockFile:
    def __init__(self, path, timeout = None, wait_interval = 1):
        self.path = path
        self.timeout = timeout
        self.wait_interval = wait_interval
        self.file = None

    def acquire(self):
        if self.file:
            raise RuntimeError(f"[LockFile] Lock already acquired on {self.path}")

        self.file = open(self.path, "a")
        start_time = time.time()

        while True:
            try:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if self.timeout and (time.time() - start_time) >= self.timeout:
                    raise TimeoutError(f"[LockFile] Timeout while waiting to acquire lock on {self.path}")

                log("LockFile", f"Waiting for lock: {self.path}")
                time.sleep(self.wait_interval)

        atexit.register(self.release)
        signal.signal(signal.SIGTERM, lambda *_: self.release())
        signal.signal(signal.SIGINT, lambda *_: self.release())

    def release(self):
        try:
            if self.file:
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
                self.file.close()
                self.file = None
                log("LockFile", f"Released lock: {self.path}")
        except Exception as e:
            log("LockFile", f"Error releasing lock: {e}")

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
