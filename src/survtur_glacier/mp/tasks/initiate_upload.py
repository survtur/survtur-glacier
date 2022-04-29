import datetime
import logging
import os.path
import threading
from io import BytesIO
from typing import TypedDict, List

from ...common.helpers import MB
from ...common.human_readable import human_readable_bytes
from ...common.iopart2 import ReadProgressInfo
from ...glacier.hasher import sha256_tree_hash_hex
from ...glacier.inventory import Inventory, ArchiveInfo
from . import id_gen
from .abstract import AbstractTransferTask
from .errors import AcceptableTaskError
from .upload_part import UploadPartTaskDict
from ..stubs import TaskStatus, TaskMetaDict, TaskType, TaskPriority, TaskCategory, CommonTaskDict

_logger = logging.getLogger(__name__)


class Duplicate(AcceptableTaskError):
    new_file: str = ""
    existing_files: List[str] = []


class InitiateUploadTaskDict(TypedDict):
    vault_name: str
    vault_arn: str
    file: str
    save_as_path: str
    save_as_name: str
    check_for_duplicates: bool


class InitiateArchiveUploadTask(AbstractTransferTask):
    data: InitiateUploadTaskDict
    percent: int = 0
    last_status_update = datetime.datetime.now()
    size: int
    sha256: str = ""
    part_hashes: List[str]

    def process(self):
        self.data = self.original_dict['data']
        self.emit_progress("Preparing…", 0)
        file = self.data['file']
        is_dir = os.path.isdir(file)

        self.size = 1 if is_dir else os.path.getsize(file)

        self._calculate_hash()
        if not is_dir and self.data['check_for_duplicates']:
            self._exit_on_duplicate()
        _logger.info(f"Initiating upload {self.data['save_as_path']}{self.data['save_as_name']}")
        if is_dir or self.size <= self.config.chunk_size_mb * MB:
            self._upload_in_one_step()
        else:
            self._initiate_multipart_upload()

    def _calculate_hash(self):
        # FastGlacier's way of hashing directories
        if os.path.isdir(self.data['file']):
            self.sha256 = sha256_tree_hash_hex(BytesIO(b"0"), chunk_size_mb=1)[0]
            return

        def hashing_callback(bytes_read: int):
            now = datetime.datetime.now()
            if (now - self.last_status_update).total_seconds() > 0.2:
                self.last_status_update = now
                percent = int(100 * bytes_read / self.size)
                percent = min(100, percent)
                self.percent = percent
                self.emit_progress(f"Checksum {percent}%", percent)

        with open(self.data['file'], mode='br') as f:
            self.sha256, self.part_hashes = sha256_tree_hash_hex(
                readable_io=f,
                chunk_size_mb=self.config.chunk_size_mb,
                progress_cb=hashing_callback if self.size > 0 else None)

    def _process_cb(self, i: ReadProgressInfo):
        now = datetime.datetime.now()
        if (now - self.last_status_update).total_seconds() > 0.2:
            self.last_status_update = now
            read = i.total_read % self.size
            percent = int(100 * read / self.size)
            percent = min(100, percent)
            hr = human_readable_bytes(read)
            self.emit_progress(f"Uploading {hr} {percent}%", percent)

    def _upload_in_one_step(self):
        file = self.data['file']
        archive_id: str = self.glacier.upload_archive(
            vault_name=self.data['vault_name'],
            file=file,
            checksum=self.sha256,
            save_name=self.data['save_as_path'] + self.data['save_as_name'],
            use_glacier_format=self.config.fast_glacier_style_naming,
            progress_cb=self._process_cb
        )

        inv = self.get_inventory()
        is_dir = os.path.isdir(file)
        a = ArchiveInfo(
            archive_id=archive_id,
            parent=self.data['save_as_path'],
            name=self.data['save_as_name'],
            upload_timestamp=datetime.datetime.now().timestamp(),
            modified_timestamp=os.path.getmtime(file),
            sha256=self.sha256,
            size=self.size,
            is_dir=is_dir
        )
        with threading.Lock():
            inv.put_archive(a)
            inv.save()
            inv.close()

        self.emit_progress("Uploaded", 0, TaskStatus.SUCCESS)

    def _initiate_multipart_upload(self):
        upload_id = self.glacier.initiate_archive_upload(file=self.data['file'],
                                                         vault_name=self.data['vault_name'],
                                                         save_as=self.data['save_as_path'] + self.data['save_as_name'],
                                                         use_glacier_format=self.config.fast_glacier_style_naming,
                                                         part_size_mb=self.config.chunk_size_mb)

        part_size = self.config.chunk_size_mb * MB
        filename = os.path.basename(self.data['file'])
        group_id = id_gen.group_id(filename)
        total_parts = len(self.part_hashes)
        for part_index, part_hash in enumerate(self.part_hashes):
            part_offset = part_index * part_size
            data = UploadPartTaskDict(
                vault_arn=self.data['vault_arn'],
                vault_name=self.data['vault_name'],
                file=self.data['file'],
                original_file_size=self.size,
                sha256_of_file=self.sha256,
                sha256_of_part=part_hash,
                part_offset=part_offset,
                part_size=min(self.size - part_offset, part_size),
                total_parts_count=total_parts,
                upload_id=upload_id,
                part_index=part_index,
                save_as_name=self.data['save_as_name'],
                save_as_path=self.data['save_as_path'],
            )

            meta = TaskMetaDict(
                id=id_gen.task_id(),
                group_id=group_id,
                name=f"Upload {filename} {part_index + 1}/{total_parts}",
                type=TaskType.ARCHIVE_PART_UPLOAD,
                priority=TaskPriority.UPLOAD_FILE,
                start_after=0,
                created=datetime.datetime.now().timestamp(),
                category=TaskCategory.UPLOAD
            )

            new_task = CommonTaskDict(
                meta=meta,
                data=data
            )

            self.queue_of_tasks_to_be_added.put(new_task)

        self.emit_progress('', 0, TaskStatus.REMOVED_SILENTLY)

    def _exit_on_duplicate(self):
        """
        :raises Duplicate
        """

        inv = self.get_inventory()

        same = list(inv.find(size=self.size, sha256_tree_hash=self.sha256))
        if not same:
            return

        dupes = [s['parent'] + s['name'] for s in same]
        self.emit_progress(f"Same file exists: {','.join(dupes)}", 0, TaskStatus.ERROR)

        err = Duplicate([s['parent'] + s['name'] for s in same])
        err.existing_files = same
        err.new_file = self.data['file']
        raise err

    def get_inventory(self) -> Inventory:
        inv_file = self.glacier.inventory_filename(self.data['vault_arn'])
        inv_file_full = self.config.get_inventories_location(inv_file)
        return Inventory(inv_file_full)
