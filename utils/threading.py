import threading
import queue
import time
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ThreadManager:
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}
        self.task_id_counter = 0
        self.lock = threading.Lock()

    def submit_task(self, func, *args, **kwargs):
        """Submit a task to the thread pool"""
        with self.lock:
            task_id = self.task_id_counter
            self.task_id_counter += 1
            
            future = self.executor.submit(func, *args, **kwargs)
            self.tasks[task_id] = {
                'future': future,
                'status': 'pending',
                'start_time': time.time()
            }
            return task_id

    def get_task_status(self, task_id):
        """Get status of a task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
                
            if task['future'].done():
                task['status'] = 'completed' if not task['future'].exception() else 'failed'
            return task['status']

    def get_task_result(self, task_id):
        """Get result of a completed task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or not task['future'].done():
                return None
                
            try:
                return task['future'].result()
            except Exception as e:
                logger.error(f"Task failed: {str(e)}")
                return None

    def cancel_task(self, task_id):
        """Cancel a pending task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task and not task['future'].done():
                task['future'].cancel()
                task['status'] = 'cancelled'
                return True
            return False

    def shutdown(self):
        """Shutdown the thread manager"""
        self.executor.shutdown(wait=False)
        self.tasks.clear()

class SafeQueue:
    """Thread-safe queue implementation"""
    def __init__(self):
        self.queue = queue.Queue()
        self.lock = threading.Lock()

    def put(self, item):
        with self.lock:
            self.queue.put(item)

    def get(self, block=True, timeout=None):
        with self.lock:
            return self.queue.get(block, timeout)

    def size(self):
        with self.lock:
            return self.queue.qsize()

    def empty(self):
        with self.lock:
            return self.queue.empty()

    def clear(self):
        with self.lock:
            while not self.queue.empty():
                self.queue.get()
