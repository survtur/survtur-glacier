import enum
from typing import TypedDict, Union

from .tasks.id_gen import TaskId, GroupId


class TaskPriority(enum.IntEnum):
    META = 0
    CREATE_DIRECTORY = 10
    DOWNLOAD_FILE = 20
    UPLOAD_FILE = 20
    INITIATE_UPLOAD = 30


class TaskType(enum.Enum):
    DUMMY = "DUMMY"
    INVENTORY_REQUEST = "INVENTORY_REQUEST"
    INVENTORY_RECEIVE = "INVENTORY_RECEIVE"
    ARCHIVE_REQUEST = "ARCHIVE_REQUEST"
    ARCHIVE_RECEIVE = "ARCHIVE_RECEIVE"
    ARCHIVE_UPLOAD = "ARCHIVE_UPLOAD"
    ARCHIVE_PART_UPLOAD = "ARCHIVE_PART_UPLOAD"


class TaskCategory(enum.Enum):
    DOWNLOAD = "DOWNLOAD"
    UPLOAD = "UPLOAD"
    META = "META"


class TaskStatus(enum.Enum):
    CREATED = enum.auto()
    WAITING = enum.auto()
    ACTIVE = enum.auto()
    SUCCESS = enum.auto()
    ERROR = enum.auto()
    REMOVED_SILENTLY = enum.auto()  # When task was removed and new task was created instead
    CANCELLED = enum.auto()


class TaskMetaDict(TypedDict):
    id: TaskId

    # Upload task may consist of few tasks. One task for each upload part of big file.
    # In order to cancel these tasks, we have to cancel all tasks with same group.
    group_id: GroupId

    name: str  # Task display name
    type: TaskType
    priority: int

    start_after: int
    created: Union[int, float]

    # It will help to pick task.
    # Imagine you have upload channel full, then pick another one Download
    # Exists, but NOT IMPLEMENTED
    category: TaskCategory


class TaskOutputDict(TypedDict):
    meta: TaskMetaDict
    percent: float
    string: str
    status: TaskStatus


class CommonTaskDict(TypedDict):
    meta: TaskMetaDict
    data: dict


class TaskErrorInfoDict(TypedDict):
    code: str
    message: str
    traceback: str


