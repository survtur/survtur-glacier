from abc import abstractmethod
from typing import List

from PyQt5.QtCore import QAbstractTableModel

from ...glacier.inventory import ArchiveInfo


class InventoryModelBase(QAbstractTableModel):

    @abstractmethod
    def selected_archives(self, row_indexes: List[int]) -> List[ArchiveInfo]:
        pass

    @abstractmethod
    def selected_archives_with_children(self, row_indexes: List[int]) -> List[ArchiveInfo]:
        pass
