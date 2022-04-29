import random
import time
from typing import TypedDict

from ..stubs import TaskOutputDict, TaskStatus
from .abstract import AbstractTask


class DummyTaskDataDict(TypedDict):
    n: int


class DummyTask(AbstractTask):

    def process(self):
        data: DummyTaskDataDict = self.original_dict['data']
        delays = 0.1 * random.random()

        steps = data['n'] * 7

        for i in range(steps):
            percent = 100 * i / steps
            output: TaskOutputDict = {
                'meta': self.original_dict['meta'],
                'percent': percent,
                'string': f"Fooling {percent:0.1f}%…",
                'status': TaskStatus.ACTIVE,
            }
            self.output_queue.put(output)
            time.sleep(delays)
            if random.random() < 0.1:
                raise RuntimeError("Ops")

        almost: TaskOutputDict = {
            'meta': self.original_dict['meta'],
            'percent': 99,
            'string': f"Almost ready…",
            'status': TaskStatus.ACTIVE,
        }
        self.output_queue.put(almost)
        time.sleep(0.2)
        done: TaskOutputDict = {
            'meta': self.original_dict['meta'],
            'percent': 0,
            'string': f"Yippee Ki Yay!",
            'status': TaskStatus.SUCCESS,
        }
        self.output_queue.put(done)
