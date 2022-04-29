import multiprocessing
import threading
from queue import Queue
from typing import Callable, Any

from .stubs import TaskOutputDict, CommonTaskDict


class OutputProcessor(threading.Thread):
    tasks_queue: 'Queue[CommonTaskDict]'
    output_queue: 'multiprocessing.Queue[TaskOutputDict]'
    on_output: Callable[[TaskOutputDict], Any]
    
    stop = threading.Event()

    def run(self):
        while True:
            if self.stop.is_set():
                break
            got: TaskOutputDict = self.output_queue.get()
            if self.stop.is_set():
                break
            self.on_output(got)
