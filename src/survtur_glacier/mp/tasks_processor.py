import logging
import multiprocessing
import threading
import time
from typing import Optional, Dict

from .one_task import process_task
from .sqlite_tasks_queue import SqliteTasksQueue, QueueExit
from .stubs import TaskOutputDict, CommonTaskDict, TaskStatus
from ..common.config import Config

_logger = logging.getLogger(__name__)


class TasksProcessor(threading.Thread):
    tasks_queue: SqliteTasksQueue
    queue_of_tasks_to_be_added: 'multiprocessing.Queue[CommonTaskDict]'
    output_queue: 'multiprocessing.Queue[TaskOutputDict]'
    current_process: Optional[multiprocessing.Process] = None
    current_task_id: str = ""
    config: Config
    tasks_to_cancel: Dict[str, int]

    def run(self):
        while True:

            try:
                d: CommonTaskDict = self.tasks_queue.get()
            except QueueExit:
                _logger.info(f'TasksProcessor #{self.native_id} STOPPED (QueueExit)')
                break

            kwargs = dict(d=d,
                          queue_of_tasks_to_be_added=self.queue_of_tasks_to_be_added,
                          output_queue=self.output_queue,
                          config=self.config)
            p = multiprocessing.Process(target=process_task, kwargs=kwargs)
            self.current_process = p
            self.current_task_id = d['meta']['id']
            p.start()
            manually_terminated = False
            while True:

                if self.current_task_id in self.tasks_to_cancel:
                    del self.tasks_to_cancel[self.current_task_id]
                    p.terminate()
                    self._emit_error(d)
                    manually_terminated = True
                    break

                time.sleep(0.5)
                if not p.is_alive():
                    break

            if p.exitcode == 0:
                _logger.debug(f'{p} task success')
                self.tasks_queue.task_done(task_id=d['meta']['id'])
                continue

            if manually_terminated:
                _logger.info(f'{p} task terminated manually (cancelled)')
                continue

            if p.exitcode == -15 or manually_terminated:
                _logger.info(f'{p} task terminated')
                continue

            self.tasks_queue.allow_next_task()
            if p.exitcode == 1:
                _logger.info(f"{p} task was faulty")
            else:
                raise RuntimeError(f'{p} returned unknown exit code: {p.exitcode}')

    def _emit_error(self, d: CommonTaskDict):
        t = TaskOutputDict(
            meta=d['meta'],
            percent=0,
            string="Cancelled",
            status=TaskStatus.ERROR
        )
        self.output_queue.put(t)
