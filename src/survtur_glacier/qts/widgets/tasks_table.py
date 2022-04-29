import datetime
import enum
from typing import TypedDict, Dict, List, Optional, Set

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QProgressBar, QHeaderView, QWidget, QMenu, QStyle, QAction

from ...mp.stubs import TaskStatus, TaskMetaDict, TaskOutputDict


class _TaskWidgetsDict(TypedDict):
    name: QTableWidgetItem
    progress_bar: QProgressBar
    status: TaskStatus


class ShowTasksThat(enum.Enum):
    ACTIVE = {TaskStatus.ACTIVE, TaskStatus.CREATED, TaskStatus.WAITING}
    SUCCEED = {TaskStatus.SUCCESS}
    FAULTY = {TaskStatus.ERROR}


class TasksTable(QTableWidget):
    _tasks: Dict[str, _TaskWidgetsDict] = {}
    _rows_to_task_id: List[str] = []
    _status_to_show: ShowTasksThat = ShowTasksThat.ACTIVE

    delete_tasks = QtCore.pyqtSignal(list)
    counters_update = QtCore.pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = ...) -> None:
        super().__init__(parent)
        self._counters = {n: 0 for n in ShowTasksThat}
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_tasks_that(self, statuses_to_show: ShowTasksThat):
        self.clearSelection()
        self._status_to_show = statuses_to_show
        for task_id, info in self._tasks.items():
            self._set_visibility(task_id, info['status'])

    def update_task(self, t: TaskOutputDict):

        task_id = t['meta']['id']
        if task_id in self._tasks:
            original_status = self._tasks[task_id]['status']
        else:
            original_status = None

        self._update(t)
        new_status = t['status']
        self._set_visibility(task_id, new_status)
        self._update_counters(original_status, new_status)

    def _set_visibility(self, task_id: str, task_status: TaskStatus):
        try:
            row_index = self._tasks[task_id]['name'].row()
        except KeyError:
            return

        if task_status in self._status_to_show.value:
            self.showRow(row_index)
        else:
            self.hideRow(row_index)

    def _update(self, t: TaskOutputDict):
        status = t['status']

        if status == TaskStatus.CREATED:
            self._create_task(t['meta'])
            return

        if status == TaskStatus.REMOVED_SILENTLY:
            self._quiet_remove_task(t['meta']['id'])
            return

        if status == TaskStatus.ACTIVE:
            pass
        elif status == TaskStatus.WAITING:
            self._mark_task_with_color(t['meta']['id'], Qt.gray)
        elif status == TaskStatus.SUCCESS:
            self._mark_task_with_color(t['meta']['id'], Qt.darkGreen)
        elif status == TaskStatus.ERROR:
            self._mark_task_with_color(t['meta']['id'], Qt.red)

        else:
            raise NotImplementedError(status)

        tw: _TaskWidgetsDict = self._tasks[t['meta']['id']]
        tw['status'] = t['status']
        tw['progress_bar'].setValue(t['percent'])
        tw['progress_bar'].setFormat(t['string'])
        tw['progress_bar'].setToolTip(t['string'])

    def _create_task(self, tm: TaskMetaDict):
        i = self.rowCount()
        if i == 0:
            self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
            self.horizontalHeader().resizeSection(1, 200)

        # Inserting row at the end. Inserting task at the end.
        self.insertRow(i)
        self._rows_to_task_id.append(tm['id'])

        name_widget = QTableWidgetItem(tm['name'])
        name_widget.setToolTip(tm['name'])
        self.setItem(i, 0, name_widget)
        pb = QProgressBar()
        planned = datetime.datetime.fromtimestamp(tm['start_after'])
        if planned > datetime.datetime.now():
            pb.setFormat('Planned after ' + planned.strftime("%H:%M:%S"))
        else:
            pb.setFormat("Waiting")
        pb.setValue(0)
        self.setCellWidget(i, 1, pb)
        tw = _TaskWidgetsDict(
            name=name_widget,
            progress_bar=pb,
            status=TaskStatus.WAITING,
        )
        self._tasks[tm['id']] = tw

    def _mark_task_with_color(self, task_id: str, color: Qt.GlobalColor):
        w = self._tasks[task_id]
        w['name'].setForeground(color)
        pb: QProgressBar = w['progress_bar']
        pal = pb.palette()
        pal.setColor(pal.Active, pal.Text, color)
        pal.setColor(pal.Active, pal.HighlightedText, color)
        # pal.setColor(pal.Active, pal.Highlight, Qt.yellow)
        pb.setValue(0)
        pb.setPalette(pal)

    def _quiet_remove_task(self, task_id: str):
        w = self._tasks.pop(task_id)
        row_index = w['name'].row()
        self.removeRow(row_index)
        self._rows_to_task_id.pop(row_index)

    def _recalculate_counters(self):
        self._counters = {n: 0 for n in ShowTasksThat}
        for t in self._tasks.values():
            for sh in ShowTasksThat:
                if t['status'] in sh.value:
                    self._counters[sh] += 1

        self.counters_update.emit(self._counters)

    def _update_counters(self, old: TaskStatus, new: TaskStatus):
        if old == new:
            return
        for s in ShowTasksThat:
            if old in s.value:
                self._counters[s] -= 1
            if new in s.value:
                self._counters[s] += 1

        self.counters_update.emit(self._counters)

    def show_context_menu(self, p: QPoint):
        selection = self._selected_rows()

        has_faulty = self._status_to_show == ShowTasksThat.FAULTY and self._counters[ShowTasksThat.FAULTY]
        has_succeed = self._status_to_show == ShowTasksThat.SUCCEED and self._counters[ShowTasksThat.SUCCEED]
        has_active = self._status_to_show == ShowTasksThat.ACTIVE and self._counters[ShowTasksThat.ACTIVE]

        all_selected = len(selection) == self._counters[self._status_to_show]
        maybe_all = len(selection) <= 1 and not all_selected

        menu = QMenu()

        if maybe_all and not has_succeed:
            select_all = QAction("Select all")
            select_all.triggered.connect(self.selectAll)
            menu.addAction(select_all)
            menu.addSeparator()

        if has_active and selection:
            text = "Cancel selected"
            if len(selection) > 1:
                text += f" ({len(selection)})"
            cancel_selected = QAction(self._icon(QStyle.SP_DialogNoButton), text)
            cancel_selected.triggered.connect(lambda: print(1/0))
            menu.addAction(cancel_selected)

        if has_faulty and selection:
            text = "Delete selected"
            if len(selection) > 1:
                text += f" ({len(selection)})"
            delete_selected = QAction(self._icon(QStyle.SP_TrashIcon), text)
            delete_selected.triggered.connect(self.delete_selected)
            menu.addAction(delete_selected)

        if has_succeed:
            text = "Clear all succeed tasks"
            clear_all_succeed = QAction(self._icon(QStyle.SP_LineEditClearButton), text)
            clear_all_succeed.triggered.connect(self.clear_all_succeed)
            menu.addAction(clear_all_succeed)

        if menu.actions():
            menu.exec(QCursor.pos())
            menu.deleteLater()

    def _selected_rows(self) -> Set[int]:
        selection = set()
        selection.update((i.row() for i in self.selectedIndexes()))
        return selection

    def delete_selected(self):
        # Collect IDs then remove
        for_del = []
        for i in self._selected_rows():
            for_del.append(self._rows_to_task_id[i])

        for task_id in for_del:
            self._quiet_remove_task(task_id)
        self.delete_tasks.emit(for_del)
        self._recalculate_counters()

    def clear_all_succeed(self):
        for_del = []
        for task_id, t in self._tasks.items():
            if t['status'] == TaskStatus.SUCCESS:
                for_del.append(task_id)

        for task_id in for_del:
            self._quiet_remove_task(task_id)

        self._recalculate_counters()

    def _icon(self, qstyle_standard_pixmap):
        return self.style().standardIcon(qstyle_standard_pixmap)
