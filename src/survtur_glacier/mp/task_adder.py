import logging
import multiprocessing
import threading
from typing import List

from .stubs import TaskOutputDict
from .sqlite_tasks_queue import SqliteTasksQueue
from .stubs import CommonTaskDict, TaskStatus

_logger = logging.getLogger(__name__)


class TaskAdder(threading.Thread):
    """
    Gets tasks from `queue_of_tasks_to_be_added` and puts it into `tasks_queue`.
    Also sends information to output_queue that new task was created.

    Has `stop` event to stop thread.  If you don't want exception about empty queue to be raised,
    add something to queue before stopping. Don't forget to do it inside threading.Lock():

    |  with threading.Lock():
    |    task_adder.queue_of_tasks_to_be_added.put("something")
    |    task_adder.stop()

    """

    tasks_queue: SqliteTasksQueue
    queue_of_tasks_to_be_added: 'multiprocessing.Queue[CommonTaskDict]'
    output_queue: 'multiprocessing.Queue[TaskOutputDict]'

    stop = threading.Event()

    def run(self):
        while True:
            if self.stop.is_set():
                break
            tasks: List[CommonTaskDict] = self._collect_tasks_group()
            if self.stop.is_set():
                break

            self.tasks_queue.put(tasks)
            for t in tasks:
                _logger.debug(f'Added task {t["meta"]["name"]}')
                self.output_queue.put({
                    'meta': t['meta'],
                    'percent': 0,
                    'string': '',
                    'status': TaskStatus.CREATED
                })

        _logger.info(f"TaskAdder #{self.native_id} STOPPED")

    def _collect_tasks_group(self) -> List[CommonTaskDict]:
        collected: List[CommonTaskDict] = []
        while True:
            collected.append(self.queue_of_tasks_to_be_added.get())
            if self.queue_of_tasks_to_be_added.empty():
                break
        return collected
