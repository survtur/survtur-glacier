import logging
from datetime import datetime
from typing import List, NamedTuple, Any, Callable, Optional

from PyQt5 import QtCore
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QStyle, QApplication

from ...glacier.inventory import Inventory, ArchiveInfo
from ...qts.widgets.inventory_model_base import InventoryModelBase

_logger = logging.getLogger(__name__)


class _ColumnData(NamedTuple):
    db_field_name: str
    column_name: str
    display_conversion_fn: Optional[Callable]
    alignment: Qt.Alignment


def _name_converter(s: str) -> str:
    parts = s.split("/")
    if s.endswith("/"):
        return parts[-2]
    return parts[-1]


class InventoryModel(InventoryModelBase):
    _columns: List[_ColumnData] = [
        _ColumnData("name", "Name",
                    display_conversion_fn=None,
                    alignment=Qt.AlignLeft | Qt.AlignVCenter),
        _ColumnData("size", "Size",
                    display_conversion_fn=lambda _: f"{_:,}".replace(',', "'"),
                    # display_conversion_fn=lambda _: human_readable_bytes(_) if _ is not None else None,
                    alignment=Qt.AlignRight | Qt.AlignVCenter),
        _ColumnData("modified_timestamp", "Modified",
                    display_conversion_fn=lambda ts: datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                    alignment=Qt.AlignHCenter | Qt.AlignVCenter),
        _ColumnData("upload_timestamp", "Uploaded",
                    display_conversion_fn=lambda ts: datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                    alignment=Qt.AlignHCenter | Qt.AlignVCenter),
    ]

    _sort_field_name: str = "name"
    _sort_asc: bool = True

    _inventory: Inventory
    _filter: str = ""
    _display_data: List[ArchiveInfo] = []
    _current_path = ""

    current_path_changed = QtCore.pyqtSignal(str)

    def current_folder_content(self) -> List[ArchiveInfo]:
        return self._display_data

    def set_inventory(self, db_file: str):
        self._inventory = Inventory(db_file)
        self._current_path = ""
        self.rebuild_data()

    def apply_filter(self, f: str):
        if f == self._filter:
            return
        self._filter = f
        self.rebuild_data()

    def get_inventory(self) -> Inventory:
        return self._inventory

    def get_current_path(self) -> str:
        return self._current_path

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._display_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        i = index.row()
        col = index.column()
        field = self._columns[col]
        item = self._display_data[i]

        if role == Qt.DisplayRole:
            value = item[field.db_field_name]
            if field.display_conversion_fn and value is not None:
                value = field.display_conversion_fn(value)
            return value

        if role == Qt.DecorationRole and col == 0:
            if not item['is_dir']:
                return QApplication.style().standardIcon(QStyle.SP_FileIcon)
            elif item['name'] == "..":
                return QApplication.style().standardIcon(QStyle.SP_FileDialogBack)
            else:
                return QApplication.style().standardIcon(QStyle.SP_DirIcon)

        if role == Qt.TextAlignmentRole:
            return self._columns[col].alignment

        if role == Qt.ToolTipRole:
            return str(item[field.db_field_name])

        return None

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        return self.createIndex(row, column, parent)

    def sort(self, column: int, order: Qt.SortOrder = ...) -> None:
        self._sort_field_name = self._columns[column].db_field_name
        self._sort_asc = order != Qt.AscendingOrder  # I don't know why, but sorting looks well only with !=
        self.rebuild_data()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> Any:
        if orientation != Qt.Vertical:
            if role == Qt.DisplayRole:
                return self._columns[section].column_name

    def enter_into_index(self, index: QModelIndex):
        if self._filter:
            return
        item_data = self._display_data[index.row()]
        if item_data['is_dir']:
            if item_data['name'] == "..":
                self._current_path = self._current_path.rstrip("/")
                self._current_path = "/".join(self._current_path.split("/")[:-1])
                if self._current_path:
                    self._current_path += "/"
            else:
                self._current_path += item_data['name']

            self.rebuild_data()

    def rebuild_data(self):
        self.beginResetModel()
        if self._filter:
            replace = self._filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").replace("*", "%")
            archives = list(self._inventory.find_archives("%" + replace + "%",
                                                          sort_by=self._sort_field_name,
                                                          asc=self._sort_asc))
        else:
            archives = list(self._inventory.get_path_content(self._current_path,
                                                             sort_by=self._sort_field_name,
                                                             asc=self._sort_asc))

            # Join folders with files
        self._display_data = []
        if self._current_path != "" and not self._filter:
            self._display_data.append(ArchiveInfo(archive_id="", parent="", name='..', upload_timestamp=None,
                                                  modified_timestamp=None,
                                                  sha256="", size=None, is_dir=True))

        for a in archives:
            self._display_data.append(a)

        self.endResetModel()
        self.current_path_changed.emit(self._current_path)

    def selected_archives(self, row_indexes: List[int]) -> List[ArchiveInfo]:
        selected = [self._display_data[i] for i in row_indexes]
        return selected

    def selected_archives_with_children(self, row_indexes: List[int]) -> List[ArchiveInfo]:
        """Returns items and all their children"""
        selected = self.selected_archives(row_indexes)
        selected = [a for a in selected if a['upload_timestamp'] is not None]
        for s in selected.copy():
            selected.extend(self._get_subcontent(s))
        _logger.info(f"Total archives{len(selected)}")
        return selected

    def _get_subcontent(self, archive: ArchiveInfo) -> List[ArchiveInfo]:
        """Returns children of this archive."""
        if not archive['is_dir']:
            return []

        out = []

        children_iter = self._inventory.get_path_content(archive['parent'] + archive['name'])

        for child in children_iter:
            out.append(child)
            out.extend(self._get_subcontent(child))

        return out

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled
