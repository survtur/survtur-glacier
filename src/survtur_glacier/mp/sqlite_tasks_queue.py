import json
import logging
import queue
import sqlite3
import threading
from time import time
from typing import Set, List, Optional, Union

from .stubs import CommonTaskDict, TaskCategory, TaskType

_logger = logging.getLogger(__name__)


class QueueExit(BaseException):
    pass


class SqliteTasksQueue(queue.Queue):

    def __init__(self, database_file, maxsize: int = 0, ) -> None:
        self._lock = threading.RLock()
        self.database_file = database_file
        self._exit_requested = False
        self._timers: Set[threading.Timer] = set()
        super().__init__(maxsize)
        self.unfinished_tasks = self._qsize()

    def get_all_tasks_in_queue(self) -> List[CommonTaskDict]:
        with self._lock:
            cur = self.db.execute("SELECT json FROM tasks WHERE executing = 0 ORDER BY priority")
            tasks = []
            for j in cur:
                tasks.append(json.loads(j[0]))
        return tasks

    def allow_next_task(self):
        super().task_done()

    def task_done(self, task_id: str = "") -> None:
        if not task_id:
            raise RuntimeError("Please, add task_id parameter to task_done()")

        with self._lock:
            self.db.execute("BEGIN EXCLUSIVE")
            cur = self.db.execute("DELETE FROM tasks WHERE task_id=:task_id", {'task_id': task_id})
            self.db.execute('COMMIT')

            assert cur.rowcount == 1, cur.rowcount
        super().task_done()

    # Override these methods to implement other queue organizations
    # (e.g. stack or priority queue).
    # These will only be called with appropriate locks held

    # Initialize the queue representation
    def _init(self, maxsize):
        with self._lock:
            self.db = sqlite3.connect(self.database_file, check_same_thread=False, isolation_level='EXCLUSIVE')
            self.db.executescript("""
                BEGIN TRANSACTION;
                CREATE TABLE IF NOT EXISTS "tasks" (
                    "task_id"	TEXT NOT NULL UNIQUE,
                    "group_id"	TEXT NOT NULL,
                    "priority"	INTEGER NOT NULL,
                    "category"	TEXT NOT NULL,
                    "name"	TEXT NOT NULL,
                    "executing" INTEGER NOT NULL,
                    "start_after"   INTEGER NOT NULL,
                    "json"	    TEXT NOT NULL,
                    "created" NUMERIC NOT NULL,
                    PRIMARY KEY("task_id")
                );
                CREATE INDEX IF NOT EXISTS "priority_index" ON "tasks" (
                    "priority"	ASC
                );
                CREATE INDEX IF NOT EXISTS "executing_index" ON "tasks" (
                    "executing"	ASC
                );
                CREATE INDEX IF NOT EXISTS "group_id_index" ON "tasks" (
                    "group_id"	ASC
                );
                CREATE INDEX IF NOT EXISTS "created_index" ON "tasks" (
                    "created"	ASC
                );
                
                UPDATE tasks SET executing=0 WHERE executing !=0;
                
              
                CREATE TABLE IF NOT EXISTS "uploads" (
                    "upload_id" TEXT NOT NULL,
                    "part_index" INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS "pair_index" ON "uploads" (
                    "upload_id" ASC,
                    "part_index" ASC
                );
                
                COMMIT;
                """)

            self._set_initial_timers()

    def _set_initial_timers(self):
        with self._lock:
            self.db.execute("BEGIN EXCLUSIVE")
            now = int(time())
            cur = self.db.execute("SELECT task_id, start_after FROM tasks WHERE start_after>?", (now,))
            for row in cur:
                till_start = row[1] - now
                t = threading.Timer(till_start + 1, self._on_task_timer_finished, kwargs={'task_id': row[0]})
                self._timers.add(t)
                t.start()
                _logger.debug(f'Task added to timer {till_start} {row[0]}')

            self.db.execute("ROLLBACK")

    def _qsize(self):
        if self._exit_requested:
            return 1
        with self._lock:
            now = int(time())
            cursor = self.db.execute("SELECT Count(*) FROM tasks WHERE executing=0 and start_after<=:now",
                                     {"now": now})
            return cursor.fetchone()[0]

    def put(self, tasks: Union[CommonTaskDict, List[CommonTaskDict]], block=True, timeout=None):
        """Put an item into the queue.

        If optional args 'block' is true and 'timeout' is None (the default),
        block if necessary until a free slot is available. If 'timeout' is
        a non-negative number, it blocks at most 'timeout' seconds and raises
        the Full exception if no free slot was available within that time.
        Otherwise ('block' is false), put an item on the queue if a free slot
        is immediately available, else raise the Full exception ('timeout'
        is ignored in that case).
        """

        if isinstance(tasks, dict):
            tasks = [tasks]

        with self.not_full:
            if self.maxsize > 0:
                if not block:
                    if self._qsize() >= self.maxsize:
                        raise queue.Full
                elif timeout is None:
                    while self._qsize() >= self.maxsize:
                        self.not_full.wait()
                elif timeout < 0:
                    raise ValueError("'timeout' must be a non-negative number")
                else:
                    end_time = time() + timeout
                    while self._qsize() >= self.maxsize:
                        remaining = end_time - time()
                        if remaining <= 0.0:
                            raise queue.Full
                        self.not_full.wait(remaining)
            with self._lock:
                self.db.execute("BEGIN EXCLUSIVE")
                for td in tasks:

                    td['meta']['category'] = td['meta']['category'].value
                    td['meta']['type'] = td['meta']['type'].value
                    j = json.dumps(td)
                    p = td['meta']['priority']
                    i = td['meta']['id']
                    s = td['meta']['start_after']
                    c = td['meta']['category']
                    g = td['meta']['group_id']
                    n = td['meta']['name']
                    cr = td['meta']['created']

                    self.db.execute(
                        """INSERT INTO tasks(task_id,
                                             priority,
                                             json,
                                             executing, -- 0
                                             start_after,
                                             category,
                                             group_id,
                                             name,
                                             created)
                                     VALUES (:i, :p, :j, 0, :s, :c, :g, :n, :cr)""",
                        {"i": i, "p": p, "j": j, "s": s, "c": c, "g": g, "n": n, "cr": cr})
                    till_start = s - time()
                    if till_start > 0:
                        t = threading.Timer(till_start + 1, self._on_task_timer_finished, kwargs={'task_id': i})
                        self._timers.add(t)
                        t.start()
                        _logger.debug(f'Task added to timer {till_start} {i}')
                    else:
                        self.unfinished_tasks += 1
                        self.not_empty.notify()
            self.db.execute('COMMIT')

    def _on_task_timer_finished(self, task_id: str):
        """Mark task as ready to be processed"""
        with self.mutex, self._lock:
            cur = self.db.execute("SELECT executing FROM tasks WHERE task_id=?", (task_id,))
            if cur.fetchone()[0] == 0:
                self.not_empty.notify()
                _logger.debug(f'Task restored by timer {task_id}')
            else:
                _logger.warning(f'Task was already executing')
            self.unfinished_tasks += 1
            self._clean_timers()

    # Get an item from the queue
    def _get(self) -> CommonTaskDict:
        if self._exit_requested:
            raise QueueExit
        with self._lock:
            now = int(time())
            self.db.execute("BEGIN EXCLUSIVE")
            cursor = self.db.execute(
                """SELECT ROWID, json FROM tasks WHERE executing=0 and start_after<=:now
                ORDER BY priority, ROWID LIMIT 1""", {'now': now})
            rowid, j = cursor.fetchone()
            data: CommonTaskDict = json.loads(j)
            data['meta']['category'] = TaskCategory(data['meta']['category'])
            data['meta']['type'] = TaskType(data['meta']['type'])
            self.db.execute("UPDATE tasks SET executing=1 WHERE ROWID=:rowid", {"rowid": rowid})
            self.db.execute('COMMIT')

        return data

    def _clean_timers(self):
        """Forgets about finished timers"""
        timers = list(self._timers)
        for t in timers:
            if not t.is_alive():
                self._timers.remove(t)

    def stop(self):
        with self.mutex:
            for t in self._timers:
                t.cancel()
            self._exit_requested = True
            self.not_empty.notify_all()

    def find_task(self, *,
                  name: Optional[str] = None,
                  task_id: Optional[str] = None,
                  group_id: Optional[str] = None,
                  priority: Optional[str] = None,
                  category: Optional[str] = None,
                  executing: Optional[bool] = None,
                  delayed: Optional[bool] = None,
                  ) -> List[CommonTaskDict]:

        conditions = [
            ('task_id', task_id),
            ('group_id', group_id),
            ('priority', priority),
            ('category', category),
            ('name', name),
            ('executing', executing),
            ('delayed', delayed),
        ]

        conditions = [c for c in conditions if c[1] is not None]
        assert conditions
        where_part = " and ".join([f"{n}=:{n}" for (n, _) in conditions])
        where_dict = {k: v for (k, v) in conditions}
        with self._lock:
            c = self.db.execute(f"SELECT json FROM tasks WHERE {where_part} ORDER BY priority, ROWID", where_dict)
            return [json.loads(row[0]) for row in c]

    def delete_tasks(self, task_ids: List[str]):
        with self._lock:
            self.db.execute("BEGIN EXCLUSIVE")
            for tis in task_ids:
                cur = self.db.execute("DELETE FROM tasks WHERE task_id=?", (tis, ))
                if cur.rowcount == 1:
                    _logger.debug(f"Deleted task {tis}")
                else:
                    _logger.debug(f"Can't delete task {tis} - already removed")
            self.db.execute("COMMIT")

