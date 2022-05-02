import logging
import multiprocessing
import threading
import time
import typing
from typing import List, Callable, Any

from ..common.config import Config
from .progress_processor import OutputProcessor
from .sqlite_tasks_queue import SqliteTasksQueue
from .stubs import CommonTaskDict, TaskOutputDict
from .task_adder import TaskAdder
from .tasks_processor import TasksProcessor

_logger = logging.getLogger(__name__)


class TasksGeneralManager(threading.Thread):

    _task_adder_thread: TaskAdder
    _task_processor_threads: List[TasksProcessor]
    _output_processor_thread: OutputProcessor

    _tasks_queue: SqliteTasksQueue
    # Queue with task dicts. It is consumed by TaskProcessors. Fills up only with TaskAdder.

    _queue_of_tasks_to_be_added: 'multiprocessing.Queue[CommonTaskDict]'
    # Queue with task dicts that should be converted to new tasks.
    # Consumed by Task Adder. Fills up with TasksGeneralManager and TaskProcessors.

    output_queue: 'multiprocessing.Queue[TaskOutputDict]'
    # Queue with information about task progress|results.
    # Fills up with TaskProcessors and TaskAdder. Consumed by OutputProcessor.

    tp_count: int = 2
    """Max quantity of task processors. Default = 2"""

    on_output_callback: Callable[[TaskOutputDict], Any] = None

    tasks_to_cancel: typing.Dict[str, typing.Union[float, int]] = {}
    # Tasks ids that user wants co cancel. With timestamp of putting items to cancel list.
    # It is possible that task will be finished before cancellation to item will stay in this list forever.
    # I use timestamp to remove too old items from this list.

    def get_all_tasks_in_queue(self) -> List[CommonTaskDict]:
        return self._tasks_queue.get_all_tasks_in_queue()

    def __init__(self, *a, tasks_db: str = ":memory:", config: Config, **kwa):
        self._config = config
        self._tasks_queue = SqliteTasksQueue(database_file=tasks_db)
        self._queue_of_tasks_to_be_added = multiprocessing.Queue()
        super().__init__(*a, **kwa)

    def run(self):
        self.output_queue = multiprocessing.Queue()
        self._task_processor_threads = []

        for _ in range(self.tp_count):
            tp = TasksProcessor()
            tp.tasks_to_cancel = self.tasks_to_cancel
            tp.tasks_queue = self._tasks_queue
            tp.output_queue = self.output_queue
            tp.queue_of_tasks_to_be_added = self._queue_of_tasks_to_be_added
            tp.config = self._config
            tp.start()
            self._task_processor_threads.append(tp)

        self._task_adder_thread = TaskAdder()
        self._task_adder_thread.tasks_queue = self._tasks_queue
        self._task_adder_thread.queue_of_tasks_to_be_added = self._queue_of_tasks_to_be_added
        self._task_adder_thread.output_queue = self.output_queue
        self._task_adder_thread.start()

        self._output_processor_thread = OutputProcessor()
        self._output_processor_thread.output_queue = self.output_queue
        self._output_processor_thread.on_output = self._on_output
        self._output_processor_thread.start()

    def stop(self):
        with threading.Lock():
            self._tasks_queue.stop()
            for tp in self._task_processor_threads:
                if tp.current_process:
                    tp.current_process.terminate()

            self._queue_of_tasks_to_be_added.put(typing.cast(CommonTaskDict, None))
            self._task_adder_thread.stop.set()

            self.output_queue.put(typing.cast(TaskOutputDict, None))
            self._output_processor_thread.stop.set()

    def add_task(self, d: CommonTaskDict):
        self._queue_of_tasks_to_be_added.put(d)

    def _on_output(self, x):
        self.on_output_callback(x)

    def find_tasks(self, *_, **kwargs) -> List[CommonTaskDict]:
        return self._tasks_queue.find_task(**kwargs)

    def delete_tasks(self, task_ids: List[str]):
        self._tasks_queue.delete_tasks(task_ids)

    def add_tasks_to_cancel_list(self, task_ids: typing.Collection[str]):
        """
        Adds task_ids to cancel list and remove too old elements from it.
        """
        _logger.info(f"Cancelling tasks: {task_ids}")
        self.tasks_to_cancel.update({t: time.time() for t in task_ids})

        with threading.RLock():
            to_clean = []
            now = time.time()
            for task_id, created_timestamp in self.tasks_to_cancel.items():
                if now - time.time() > 600:
                    to_clean.append(task_id)
            for t in to_clean:
                _logger.warning(f"Removing task {t} from tasks_to_cancel list. Too old request.")
                del self.tasks_to_cancel[t]
