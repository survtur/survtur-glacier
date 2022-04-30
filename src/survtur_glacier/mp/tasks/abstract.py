import datetime
import logging
import multiprocessing
import time
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Callable, Any, Union

from ...common.config import Config
from ...common.human_readable import human_readable_bytes
from ...glacier.survtur_glacier import SurvturGlacier
from ...mp.stubs import CommonTaskDict, TaskStatus, TaskOutputDict
from ...mp.tasks import id_gen

_logger = logging.getLogger(__name__)


class AbstractTask(ABC):
    original_dict: CommonTaskDict
    config: Config
    output_queue: 'multiprocessing.Queue[TaskOutputDict]'

    queue_of_tasks_to_be_added: 'multiprocessing.Queue[CommonTaskDict]'
    glacier: SurvturGlacier

    @classmethod
    def from_dict(cls, *, task_dict: dict,
                  output_queue: 'multiprocessing.Queue[TaskOutputDict]',
                  queue_of_tasks_to_be_added: 'multiprocessing.Queue[CommonTaskDict]',
                  config: Config):
        task = cls()
        task.original_dict = deepcopy(task_dict)
        task.config = config
        task.output_queue = output_queue
        task.queue_of_tasks_to_be_added = queue_of_tasks_to_be_added
        task.glacier = SurvturGlacier(access_key_id=config.access_key_id,
                                      secret_access_key=config.secret_access_key,
                                      region_name=config.region_name)
        return task

    @abstractmethod
    def process(self):
        pass

    def emit_progress(self, text: str, percent: int, status: TaskStatus = TaskStatus.ACTIVE):
        self.output_queue.put({
            'meta': self.original_dict['meta'],
            'percent': percent,
            'string': text,
            'status': status
        })

    def recreate_current_task(self, retry_delay: int):
        self.emit_progress('Not ready yet', 0)
        new_meta = deepcopy(self.original_dict['meta'])
        new_meta['id'] = id_gen.task_id()
        new_meta['group_id'] = id_gen.group_id("")
        new_meta['start_after'] = int(time.time()) + retry_delay

        # show info
        name = self.original_dict['meta']['name']
        till = datetime.datetime.fromtimestamp(new_meta['start_after']).strftime("%X")
        _logger.info(f"Recreating task {name} with delay {retry_delay}s. till {till}")

        self.queue_of_tasks_to_be_added.put({
            'meta': new_meta,
            'data': self.original_dict['data']
        })
        self.emit_progress('', 0, TaskStatus.REMOVED_SILENTLY)

    def check_job(self, vault_name: str, job_id: str, processing_fn: Callable[[dict], Any], retry_delay: int) -> None:
        self.emit_progress('Checking… ', 0)
        _logger.debug(f"Checking status of job '{job_id}'…")
        j = self.glacier.describe_job(vault_name=vault_name, job_id=job_id)
        status_code = j['StatusCode']
        if status_code == 'InProgress':
            _logger.debug(f"Job '{job_id}' still in progress")
            self.recreate_current_task(retry_delay)
        elif status_code == 'Succeeded':
            processing_fn(j)
        else:
            raise NotImplementedError(status_code)


class AbstractTransferTask(AbstractTask, ABC):
    last_transfer_progress: float = 0

    def emit_transfer_progress(self, transferred: int, prefix: str,
                               planned_transfer_size: int, interval: Union[int, float] = 0.2):
        """

        :param transferred: total amount of bytes sent|received
        :param prefix: Text to write before percents
        :param planned_transfer_size:
        :param interval:
        :return:
        """

        now = time.time()
        if (now - self.last_transfer_progress) < interval:
            return

        hr_transferred = human_readable_bytes(transferred)

        if planned_transfer_size:
            percent = int(100 * transferred / planned_transfer_size)
            percent_str = f"/{percent}%"
        else:
            percent_str = ""
            percent = 0

        s = f'{prefix}{hr_transferred}{percent_str}'
        self.last_transfer_progress = now
        self.emit_progress(s, percent)
