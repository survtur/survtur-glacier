import logging
from typing import Optional

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QMimeData, Qt, QModelIndex, QPoint
from PyQt5.QtGui import QKeySequence, QCursor
from PyQt5.QtWidgets import QTableView, QHeaderView, QShortcut, QWidget, QMenu, QAction, QStyle

from ...qts.widgets.inventory_model_base import InventoryModelBase

_logger = logging.getLogger(__name__)

def _local_files_only(mime_data: QMimeData) -> bool:
    urls = mime_data.urls()
    if not urls:
        print("NO URLS")
        return False

    for u in urls:

        if not u.isLocalFile():
            print(f"NOT LOCAL: {u.path()} ")
            return False

    print(f"ALL LOCALS ({len(urls)})")
    return True


class InventoryTableView(QTableView):
    enter_or_return = QtCore.pyqtSignal(QModelIndex)
    files_dropped = QtCore.pyqtSignal(list)
    download_desired = QtCore.pyqtSignal(list)

    def _emit_enter_return(self):
        self.enter_or_return.emit(self.currentIndex())


    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent)
        QShortcut(QKeySequence(Qt.Key_Return), self, self._emit_enter_return, context=Qt.WidgetShortcut)
        QShortcut(QKeySequence(Qt.Key_Enter), self, self._emit_enter_return, context=Qt.WidgetShortcut)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def setModel(self, model: Optional[InventoryModelBase]) -> None:
        super().setModel(model)

        # Stet all columns autoresize, except first
        if model:
            for m in range(1, model.columnCount()):
                self.horizontalHeader().setSectionResizeMode(m, QHeaderView.ResizeToContents)
            self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    # On drug enter, we have to confirm that we will track that event.
    # Without e.acceptProposedAction() or e.accept() other drag events will not fire.
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        if self.model() and _local_files_only(e.mimeData()):
            self.setDisabled(True)
            e.accept()

    # Without overloading this function drop action will not fire.
    # Somehow original function will make it unacceptable.
    def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:
        pass

    def dragLeaveEvent(self, e: QtGui.QDragLeaveEvent) -> None:
        self.setDisabled(False)

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        paths = [u.path() for u in e.mimeData().urls()]
        self.files_dropped.emit(paths)
        self.setDisabled(False)

    def _selected_archives(self):
        selected = self.selectedIndexes()
        rows = set()
        for q_index in selected:
            rows.add(q_index.row())
        rows = list(rows)
        rows.sort()
        m: InventoryModelBase = self.model()
        a = m.selected_archives_with_children(rows)
        return a

    def show_context_menu(self, p: QPoint):
        if not self.model():
            return

        archives = self._selected_archives()
        menu = QMenu()

        if archives:
            select_all = QAction(self.style().standardIcon(QStyle.SP_ArrowDown), "Download to …")
            select_all.triggered.connect(lambda: self.download_desired.emit(archives))
            menu.addAction(select_all)

        menu.exec(QCursor.pos())
        menu.deleteLater()
