import datetime
import secrets
from typing import NewType

TaskId = NewType('TaskId', str)
"""
Must be unique for every task. Should be created from task_id() function.
"""

GroupId = NewType('GroupId', str)


def task_id() -> TaskId:
    s = secrets.token_urlsafe(64)
    s += " @ " + datetime.datetime.utcnow().isoformat()

    return TaskId(s)


def group_id(name: str) -> GroupId:
    return GroupId(f"{name} --- {task_id()}")
