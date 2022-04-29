import datetime
import logging
import os
import queue
import random
import re
import secrets
import time
from tempfile import NamedTemporaryFile
from typing import List, Dict, TypedDict

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QProgressBar, QShortcut, QMessageBox, QTableWidgetItem, QStyle, QInputDialog, QFileDialog

from ..common.config import Config
from ..common.human_readable import human_readable_bytes
from ..glacier.enums import GlacierFolderType
from ..glacier.hasher import sha256_tree_hash_hex
from ..glacier.inventory import Inventory, ArchiveInfo
from ..glacier.stubs.vaultdict import VaultDict
from ..glacier.survtur_glacier import SurvturGlacier, GlacierTier
from ..mp.general_manager import TasksGeneralManager
from ..mp.stubs import CommonTaskDict, TaskOutputDict, TaskStatus, TaskMetaDict, TaskType, TaskCategory, TaskPriority
from ..mp.tasks import id_gen
from ..mp.tasks.downloads import InitiateArchiveRequestTaskDataDict
from ..mp.tasks.initiate_upload import InitiateUploadTaskDict
from ..mp.tasks.inventory import InitiateInventoryRequestTaskDataDict
from .items_emitter_thread import ItemsEmitterThread
from .mainwindow import Ui_MainWindow
from .tier_dialog import TierDialog
from .widgets.inventory_model import InventoryModel
from .widgets.tasks_table import ShowTasksThat

_logger = logging.getLogger(__name__)


class _TaskWidgetsDict(TypedDict):
    name: QTableWidgetItem
    progress_bar: QProgressBar
    status: TaskStatus


def get_subcontent(f: str):
    sub = []
    for p, dirs, files in os.walk(f, followlinks=False):
        dirs = [os.path.join(p, d) for d in dirs]
        files = [os.path.join(p, f) for f in files]
        sub.extend(dirs)
        sub.extend(files)
    return sub


class SurvturGlacierGui(QtWidgets.QMainWindow, Ui_MainWindow):
    progress = QtCore.pyqtSignal(dict)
    result = QtCore.pyqtSignal(dict)
    inventory_updated = QtCore.pyqtSignal(str)

    _vault_arn_to_current_dirs: Dict[str, str]
    _upload_intention_root: str
    _upload_intention_list: List[str]

    def __init__(self, *args, workdir: str, **kwargs, ):
        super().__init__(*args, **kwargs)
        self._workdir = workdir
        self._config = Config(self._workdir)
        self._inventory_model = InventoryModel()
        self._task_widgets: Dict[str, _TaskWidgetsDict] = {}
        self.setupUi(self)
        self._init_widgets()
        self._get_vaults()
        self._init_gm()
        self._init_task_adder()

        self._setup_signals()
        self._setup_shortcuts()
        # Setup is complete. Start working now!
        self._show_vault_content()
        self._gm.start()
        self.btnActiveTasks.click()

    def _setup_signals(self):
        self.progress.connect(self.newTasksTable.update_task)
        self.progress.connect(self._monitor_progress_for_inventory_update)
        self.result.connect(_logger.info)
        self.inventory_updated.connect(self._inventory_model.set_inventory)
        self.inventory_updated.connect(self.show_inventory_date)
        self.btnActiveTasks.clicked.connect(lambda: self._show_tasks(ShowTasksThat.ACTIVE, self.btnActiveTasks))
        self.btnFaultyTasks.clicked.connect(lambda: self._show_tasks(ShowTasksThat.FAULTY, self.btnFaultyTasks))
        self.btnSucceedTasks.clicked.connect(lambda: self._show_tasks(ShowTasksThat.SUCCEED, self.btnSucceedTasks))
        self.searchLine.textChanged.connect(self._inventory_model.apply_filter)
        self.searchLine.textChanged.connect(self._show_hide_upload_buttons)
        self.vaultSelector.currentIndexChanged.connect(self._show_vault_content)
        self.inventoryView.files_dropped.connect(self.upload_desired)
        self.inventoryView.download_desired.connect(self.download_desired)
        self.newTasksTable.counters_update.connect(self.show_tasks_counters)
        self.newTasksTable.delete_tasks.connect(self._gm.delete_tasks)
        self._inventory_model.current_path_changed.connect(self.currentPathTxt.setText)
        self.btnUpload.clicked.connect(self.pick_files_to_upload)
        self.btnMkdir.clicked.connect(self.make_dir_pressed)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self.searchLine.setFocus)
        QShortcut(QKeySequence("Ctrl+*"), self, self.add_sample_tasks)

    def _init_task_adder(self):
        self._tasks_to_add_queue = queue.Queue()
        self._task_adder = ItemsEmitterThread(items=self._tasks_to_add_queue, delay=0.001)
        self._task_adder.tick.connect(self._gm.add_task)
        self._task_adder.start()

    def _init_widgets(self):

        self.inventoryView.setModel(self._inventory_model)
        self.requestInventoryBtn.clicked.connect(self.request_inventory)
        self.requestInventoryBtn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))

        self.inventoryView.doubleClicked.connect(self._inventory_model.enter_into_index)
        self.inventoryView.enter_or_return.connect(self._inventory_model.enter_into_index)


        self.btnMkdir.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))


    def _init_gm(self):
        """
        Initialize general tasks manager without starting it.
        GM should be started after at the very end of initialization.
        """
        db_file = os.path.join(self._workdir, 'survtur_glaciers_tasks.sqlite3')
        self._gm = TasksGeneralManager(tasks_db=db_file, config=self._config)
        self._gm.tp_count = self._config.task_threads
        self._gm.on_output = lambda x: self.progress.emit(x)
        self._gm.on_result = lambda x: self.result.emit(x)
        self._populate_tasks_list(self._gm.get_all_tasks_in_queue())

    def _populate_tasks_list(self, tasks: List[CommonTaskDict]):
        for t in tasks:
            initial_progress = TaskOutputDict(
                meta=t['meta'],
                percent=0,
                string='',
                status=TaskStatus.CREATED
            )
            self.newTasksTable.update_task(initial_progress)

    def upload_desired(self, files: List[str]):

        if self.searchLine.text():
            cant = QMessageBox(self)
            cant.setText("Can't upload while in search mode.\nPlease remove text from search line and try again.")
            cant.setWindowTitle("Can't")
            cant.finished.connect(cant.deleteLater)
            cant.setIcon(QMessageBox.Information)
            cant.show()
            return

        for path in files:

            if not os.path.exists(path):
                continue

            if os.path.isdir(path):
                q = QMessageBox(self)
                q.setWindowTitle("Sorry")
                q.setText(
                    "<p>Uploading folders not supported. Files only.</p>" +
                    "<p>You can create folder manually and then upload files.</p>")
                q.setIcon(QMessageBox.Information)
                q.finished.connect(q.deleteLater)
                q.open()
                return

        self._upload_intention_list = []
        self._upload_intention_root = os.path.dirname(files[0])

        for f in files:
            self._upload_intention_list.append(f)
            if os.path.isdir(f):
                self._upload_intention_list.extend(get_subcontent(f))

        total_size = 0
        dirs = []
        files = []
        ignored_links = []
        small_files = []
        for p in self._upload_intention_list:

            if os.path.isdir(p):
                dirs.append(p)
            elif os.path.islink(p):
                ignored_links.append(p)
            elif os.path.isfile:
                files.append(p)
                getsize = os.path.getsize(p)
                total_size += getsize
                if getsize < 10_000_000:
                    small_files.append(p)
            else:
                raise RuntimeError(p)

        q = QMessageBox(self)

        hr_size = human_readable_bytes(total_size)
        if len(files) == 1:
            text = f"Are you sure that you want to upload <b>{files[0]}</b> for {hr_size}?"
        elif len(files) == 0:
            text = "No files for upload."
        else:
            text = f"Are you sure that you want to upload <b>{len(files)}</b> files for {hr_size}?"

        if dirs:
            text += f"<br/>Folders to be created: {len(dirs)}."

        if ignored_links:
            text += (f"<br/><br/><b>WARNING:</b> There was symlink ({len(ignored_links)}) for upload. " +
                     "It will be ignored and not uploaded!")

        if small_files:
            text += ("<br/><br/><small>" +
                     "NOTE: AWS Glacier does it best when you upload archives, not separate files. " +
                     "Think about making single archive with them and upload it." +
                     "</small>")

        if files or dirs:
            q.setWindowTitle("Confirm upload")
            q.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            q.finished.connect(self.on_upload_confirmation_answered)
        else:
            q.setWindowTitle("Nothing to upload")
            q.setStandardButtons(QMessageBox.Close)
        q.setText(text)
        q.finished.connect(q.deleteLater)
        q.open()

    def on_check_for_duplicates_answered(self, answer: int):
        should_check_for_dupes = answer == QMessageBox.Yes

        tasks = []
        current_path = self._inventory_model.get_current_path()
        for file in self._upload_intention_list:
            name = os.path.basename(file)
            if os.path.isdir(file):
                name += "/"
            t = self._create_upload_task(file=file,
                                         save_as_path=current_path,
                                         save_as_name=name,
                                         check_duplicates=should_check_for_dupes)
            tasks.append(t)

        for t in tasks:
            self._tasks_to_add_queue.put(t)

    def on_upload_confirmation_answered(self, answer: int):
        if answer != QMessageBox.Yes:
            self._upload_intention_list = []
            return

        q = QMessageBox(self)
        q.setWindowTitle("Duplicates check")
        q.setText("<p>Prevent duplicates uploading?</p>" +
                  "<p><small>If file with same content is already in inventory, it will not be uploaded.</small></p>")
        q.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        q.setDefaultButton(QMessageBox.Yes)

        q.finished.connect(self.on_check_for_duplicates_answered)
        q.finished.connect(q.deleteLater)
        q.open()

    def add_sample_tasks(self):

        c = random.randint(1, 10)
        with_delay_count = 0
        common_part = id_gen.task_id()[:random.randint(1, 6)]
        for i in range(c):
            delay = random.choices([0, 10], weights=[3, 1])[0]
            if delay:
                with_delay_count += 1
            tid = id_gen.task_id()
            t: CommonTaskDict = {
                "meta": {"priority": TaskPriority.META,
                         "category": TaskCategory.META,
                         "created": datetime.datetime.now().timestamp(),
                         "type": TaskType.DUMMY,
                         "id": tid,
                         "group_id": id_gen.group_id(""),
                         "start_after": int(time.time() + delay) if delay else 0,
                         "name": f"Dummy task with N={i} {common_part}"},
                "data": {"n": i}
            }
            self._tasks_to_add_queue.put(t)

        _logger.info(f'{c} tasks added. Delayed {with_delay_count}. Now: {c - with_delay_count}')

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        print('stopping GM')
        self._gm.stop()
        self._gm.join()
        super().closeEvent(a0)

    def _get_survtur_glacier(self) -> SurvturGlacier:
        return SurvturGlacier(access_key_id=self._config.access_key_id,
                              secret_access_key=self._config.secret_access_key,
                              region_name=self._config.region_name)

    def _get_vaults(self):
        g = self._get_survtur_glacier()
        try:
            vaults = g.download_vaults_list()
        except Exception as e:
            _logger.exception(e)
            print("\n\n============ ERROR MESSAGE ========")
            print(str(e))
            print("===================================\n")
            print(f'Please check and update your config at {repr(self._config.get_config_file_locations())}')
            exit()
            raise e

        vaults.sort(key=lambda t: t['VaultName'])
        self._vault_arn_to_current_dirs = {}

        for v in vaults:
            if v['SizeInBytes']:
                size = human_readable_bytes(v['SizeInBytes'], "")
                self.vaultSelector.addItem(f"{v['VaultName']} - {size}", v)
            else:
                self.vaultSelector.addItem(f"{v['VaultName']} - Empty", v)

            self._vault_arn_to_current_dirs[v['VaultARN']] = ''

    def current_vault(self) -> VaultDict:
        return self.vaultSelector.currentData()

    def _show_vault_content(self):
        self.inventoryView.setModel(None)
        vault = self.current_vault()

        if not vault:
            self.requestInventoryBtn.setDisabled(True)
            return

        inventory_filename = SurvturGlacier.inventory_filename(vault['VaultARN'])
        location = self._config.get_inventories_location(inventory_filename)

        has_inventory = os.path.isfile(location)

        if has_inventory:
            request_task = self._gm.find_tasks(name=f"Get inventory of {vault['VaultName']}")
            self.requestInventoryBtn.setDisabled(bool(request_task))
            self.inventoryView.setModel(self._inventory_model)
            self.inventory_updated.emit(location)
            return

        self._show_missing_inventory(vault)

    def show_inventory_date(self, inventory_db: str):
        inv_date = Inventory(inventory_db).inventory_date
        self.inventoryStatus.setText(inv_date.strftime("Inventory date: %Y-%m-%d %H:%M:%S"))

    def _show_missing_inventory(self, v: VaultDict):
        request_task = self._gm.find_tasks(name=f"Get inventory of {v['VaultName']}")
        table_text = "Waiting for inventory update…" if request_task else "No inventory requested"
        self.inventoryStatus.setText(table_text)
        self.requestInventoryBtn.setText("Update inventory")
        self.requestInventoryBtn.setDisabled(bool(request_task))

    def request_inventory(self):
        self.requestInventoryBtn.setDisabled(True)
        self.inventoryStatus.setText("Waiting for inventory update…")
        v = self.current_vault()

        meta = TaskMetaDict(id=id_gen.task_id(),
                            group_id=id_gen.group_id(""),
                            name=f"Get inventory of {v['VaultName']}",
                            type=TaskType.INVENTORY_REQUEST,
                            priority=TaskPriority.META,
                            category=TaskCategory.META,
                            start_after=0,
                            created=datetime.datetime.now().timestamp())
        data: InitiateInventoryRequestTaskDataDict = {
            "vault_arn": v['VaultARN'],
            "vault_name": v['VaultName'],
            "format": 'CSV'
        }
        task: CommonTaskDict = {
            'meta': meta,
            'data': data
        }

        self._gm.add_task(task)

    def _create_upload_task(self, file: str, save_as_path: str, save_as_name: str,
                            check_duplicates: bool) -> CommonTaskDict:
        is_dir = os.path.isdir(file)
        if is_dir:
            name = f"Make dir {save_as_path + save_as_name}"
        else:
            size_info = human_readable_bytes(os.path.getsize(file))
            name = f"Upload {size_info} {save_as_name}"

        meta = TaskMetaDict(id=id_gen.task_id(),
                            group_id=id_gen.group_id(""),
                            name=name,
                            type=TaskType.ARCHIVE_UPLOAD,
                            priority=TaskPriority.CREATE_DIRECTORY if is_dir else TaskPriority.UPLOAD_FILE,
                            category=TaskCategory.UPLOAD,
                            start_after=0,
                            created=datetime.datetime.now().timestamp())

        v = self.current_vault()
        data = InitiateUploadTaskDict(
            vault_name=v['VaultName'],
            vault_arn=v['VaultARN'],
            file=file,
            save_as_path=save_as_path,
            save_as_name=save_as_name,
            check_for_duplicates=check_duplicates
        )

        task: CommonTaskDict = {
            'meta': meta,
            'data': data
        }

        return task

    _old_values = {}

    def show_tasks_counters(self, d: Dict[ShowTasksThat, int]):
        if self._old_values.get(ShowTasksThat.ACTIVE) != d[ShowTasksThat.ACTIVE]:
            self._old_values[ShowTasksThat.ACTIVE] = d[ShowTasksThat.ACTIVE]
            self.btnActiveTasks.setText(f"Active - {d[ShowTasksThat.ACTIVE]}")

        if self._old_values.get(ShowTasksThat.FAULTY) != d[ShowTasksThat.FAULTY]:
            self._old_values[ShowTasksThat.FAULTY] = d[ShowTasksThat.FAULTY]
            self.btnFaultyTasks.setText(f"Faulty - {d[ShowTasksThat.FAULTY]}")
            self.btnFaultyTasks.setEnabled(d[ShowTasksThat.FAULTY] > 0)
            if d[ShowTasksThat.FAULTY] > 0:
                pal = self.btnFaultyTasks.palette()
                pal.setColor(pal.Active, pal.ButtonText, Qt.red)
                self.btnFaultyTasks.setPalette(pal)
            else:
                self.btnFaultyTasks.setPalette(self.style().standardPalette())

        if self._old_values.get(ShowTasksThat.SUCCEED) != d[ShowTasksThat.SUCCEED]:
            self._old_values[ShowTasksThat.SUCCEED] = d[ShowTasksThat.SUCCEED]
            self.btnSucceedTasks.setText(f"Succeed - {d[ShowTasksThat.SUCCEED]}")
            self.btnSucceedTasks.setEnabled(d[ShowTasksThat.SUCCEED] > 0)

    def tier_selected_select_folder(self, tier: GlacierTier):
        raise NotImplementedError

    def download_desired(self, archives: List[ArchiveInfo]):
        archives.sort(key=lambda a: (a['parent'], a['name']))

        top_level = min((a['parent'] for a in archives))
        print(f"top_level: {top_level}")

        files_count = 0
        dirs_count = 0
        total_size = 0
        for a in archives:
            assert a['parent'].startswith(top_level)
            if a['is_dir']:
                dirs_count += 1
            else:
                total_size += a['size']
                files_count += 1

        d = TierDialog(self)
        d.update_label(total_size, files_count, dirs_count)
        d.accepted.connect(lambda: self.start_downloading(archives, top_level, d.selected_path, d.selected_tier))
        d.finished.connect(d.deleteLater)
        d.open()

    def start_downloading(self, archives: List[ArchiveInfo], top_level: str, save_dir: str, tier: GlacierTier):
        """

        :param archives:
        :param top_level: top path level for selected files inside inventory.
        :param save_dir:
        :param tier:
        :return:
        """
        tasks: List[CommonTaskDict] = []
        for a in archives:

            if a['is_dir']:
                continue

            meta = TaskMetaDict(
                id=id_gen.task_id(),
                group_id=id_gen.group_id("DL"),
                name=f"Download {a['name']}",
                type=TaskType.ARCHIVE_REQUEST,
                priority=TaskPriority.META,
                start_after=0,
                created=int(time.time()),
                category=TaskCategory.DOWNLOAD
            )

            relative_to_top_level = a['parent'][len(top_level):]
            dirs_to_create = relative_to_top_level.split('/')[:-1]

            data = InitiateArchiveRequestTaskDataDict(
                vault_name=self.current_vault()['VaultName'],
                archive_id=a['archive_id'],
                save_dir=save_dir,
                save_name=a['name'],
                dirs_to_create=dirs_to_create,
                hash=a['sha256'],
                tier=tier.value
            )

            task = CommonTaskDict(
                meta=meta,
                data=data,
            )

            tasks.append(task)

        for t in tasks:
            self._tasks_to_add_queue.put(t)

    def make_dir_pressed(self):
        if self._config.fast_glacier_style_dirs:
            folder_type = GlacierFolderType.FAST_GLACIER_STYLE
        else:
            folder_type = GlacierFolderType.SURVTUR_GLACIER_STYLE

        self._create_folder_dialog(folder_type)

    def _create_folder_dialog(self, folder_type: GlacierFolderType):
        d = QInputDialog(self)
        d.setInputMode(QInputDialog.TextInput)

        t = (f"<p>Enter the name for new folder.</p>" +
             f"<p><b>Name it wisely.</b> This is not regular filesystem. Folders can't be renamed or moved. " +
             f"The only way is to delete its content an upload again.</p>")

        if self._config.restricted_naming:
            t += f"<p>Only allowed characters: A-Za-z0-9_-.()[]+<b>"

        d.setLabelText(t)
        d.setWindowTitle("New folder")

        d.accepted.connect(lambda: self._make_folder(d.textValue(), folder_type))
        d.accepted.connect(d.deleteLater)
        d.show()

    def _make_folder(self, name: str, folder_type: GlacierFolderType):
        parent = self._inventory_model.get_current_path()
        inventory = self._inventory_model.get_inventory()
        try:
            self._validate_file_name(name)
        except ValueError:
            return

        if not name.endswith("/"):
            name += "/"

        assert parent == "" or parent.endswith("/"), parent
        token = secrets.token_urlsafe()
        if folder_type == GlacierFolderType.SURVTUR_GLACIER_STYLE:
            archive_id = "VIRTUAL_DIR " + token
            sha256 = "WHO CARES " + token
        elif folder_type == GlacierFolderType.FAST_GLACIER_STYLE:
            archive_id = self._upload_fast_glacier_like_folder(name, parent)
            sha256 = "WHO CARES " + token
        else:
            raise ValueError(folder_type)

        timestamp = int(time.time())

        a = ArchiveInfo(
            archive_id=archive_id,
            parent=parent,
            name=name,
            upload_timestamp=timestamp,
            modified_timestamp=timestamp,
            sha256=sha256,
            size=None,
            is_dir=True
        )
        inventory.put_archive(a)
        self.inventory_updated.emit(inventory.db_file)

    def _validate_file_name(self, name: str):
        err = ""
        if name == "." or name == ".." or name == "":
            err = "Impossible name"

        if self._config.restricted_naming:
            if re.match(r".*[^-A-Za-z0-9_.()\[\]+].*", name):
                err = "Name contains characters that not allowed."
        elif "/" in name or "\\" in name:
            err = "Slashes are not allowed."

        if not name.isprintable():
            err = "Name contains unprintable characters"

        if err:
            m = QMessageBox(self)
            m.setIcon(QMessageBox.Critical)
            m.addButton(QMessageBox.Ok)
            m.setText(err)
            m.setWindowTitle("Name problem")
            m.open()
            raise ValueError

    def _upload_fast_glacier_like_folder(self, name: str, parent: str) -> str:
        """
        Return archive_id of uploaded "archive" that represents that folder
        :param name:
        :param parent:
        :return:
        """

        save_name = parent + name

        with NamedTemporaryFile() as tf:
            tf.write(b" ")
            tf.flush()
            tf.seek(0)

            g = self._get_survtur_glacier()
            sha256, _ = sha256_tree_hash_hex(tf, 1)
            archive_id = g.upload_archive(vault_name=self.current_vault()['VaultName'],
                                          file=tf.name,
                                          checksum=sha256,
                                          save_name=save_name,
                                          use_glacier_format=self._config.fast_glacier_style_naming
                                          )

        return archive_id

    def _monitor_progress_for_inventory_update(self, t: TaskOutputDict):
        if t['status'] != TaskStatus.SUCCESS:
            return

        if t['meta']['type'] == TaskType.INVENTORY_RECEIVE:
            self.inventory_updated.emit(self._inventory_model.get_inventory().db_file)
            return

        if (
            t['status'] == TaskStatus.SUCCESS and
            t['string'] == "Uploaded" and
            t['meta']['type'] in [TaskType.ARCHIVE_UPLOAD, TaskType.ARCHIVE_PART_UPLOAD]
        ):
            self.inventory_updated.emit(self._inventory_model.get_inventory().db_file)

    def pick_files_to_upload(self):
        d = QFileDialog(self, caption="Files to upload")
        d.setFileMode(QFileDialog.ExistingFiles)
        d.filesSelected.connect(lambda: self.upload_desired(d.selectedFiles()))
        d.finished.connect(d.deleteLater)
        d.show()

    def _show_hide_upload_buttons(self, filter_str: str):
        self.btnUpload.setDisabled(bool(filter_str))
        self.btnMkdir.setDisabled(bool(filter_str))

    def _show_tasks(self, statuses_to_show: ShowTasksThat, pressed_btn: QtWidgets.QPushButton):
        for b in [self.btnActiveTasks, self.btnFaultyTasks, self.btnSucceedTasks]:
            b.setChecked(False)
        pressed_btn.setChecked(True)
        self.newTasksTable.show_tasks_that(statuses_to_show)
