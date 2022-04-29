import queue
import time
from typing import Optional, Union

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QObject


class ItemsEmitterThread(QThread):
    tick = QtCore.pyqtSignal(dict)

    def __init__(self,
                 parent: Optional[QObject] = None, *,
                 items: queue.Queue, delay: Union[float, int]
                 ) -> None:
        self._items = items
        self._delay = delay
        super().__init__(parent)

    def run(self):
        while True:
            i = self._items.get()
            self.tick.emit(i)
            time.sleep(self._delay)
