import logging
import multiprocessing

from ..common.config import Config
from .stubs import CommonTaskDict, TaskOutputDict, TaskStatus, TaskType
from .tasks.downloads import InitiateArchiveRequestTask, ReceiveArchiveTask
from .tasks.dummy import DummyTask
from .tasks.errors import AcceptableTaskError
from .tasks.initiate_upload import InitiateArchiveUploadTask
from .tasks.inventory import InitiateInventoryRequestTask, RetrieveInventoryContentTask
from .tasks.upload_part import UploadPartTask

_logger = logging.getLogger(__name__)


class UnknownTaskType(RuntimeError):
    pass


def process_task(d: CommonTaskDict,
                 queue_of_tasks_to_be_added: 'multiprocessing.Queue[CommonTaskDict]',
                 output_queue: 'multiprocessing.Queue[TaskOutputDict]',
                 config: Config):

    _logger.debug(f"Starting \"{d['meta']['name']}\"")

    try:
        t = d['meta']['type']
        if t == TaskType.INVENTORY_REQUEST:
            task_class = InitiateInventoryRequestTask
        elif t == TaskType.INVENTORY_RECEIVE:
            task_class = RetrieveInventoryContentTask
        elif t == TaskType.ARCHIVE_UPLOAD:
            task_class = InitiateArchiveUploadTask
        elif t == TaskType.ARCHIVE_PART_UPLOAD:
            task_class = UploadPartTask
        elif t == TaskType.ARCHIVE_REQUEST:
            task_class = InitiateArchiveRequestTask
        elif t == TaskType.ARCHIVE_RECEIVE:
            task_class = ReceiveArchiveTask
        elif t == TaskType.DUMMY:
            task_class = DummyTask
        else:
            raise UnknownTaskType(t.name)

        task = task_class.from_dict(task_dict=d,
                                    output_queue=output_queue,
                                    config=config,
                                    queue_of_tasks_to_be_added=queue_of_tasks_to_be_added)

        task.process()

    except AcceptableTaskError:
        # Do not print information about error.
        # Assuming that task shows something itself
        exit(1)
    except Exception as e:
        _logger.exception(e)
        output_bad: TaskOutputDict = {
            'meta': d['meta'],
            "percent": 0,
            "string": repr(e),
            "status": TaskStatus.ERROR
        }
        output_queue.put(output_bad)
        exit(1)
