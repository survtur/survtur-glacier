import mmap
import os.path
import time
import typing
from typing import TypedDict
from typing.io import IO

from ...common.iopart2 import MmapWithReadCallback, ReadProgressInfo
from ...glacier.inventory import Inventory, ArchiveInfo
from .abstract import AbstractTransferTask
from ...mp.uploads_db import UploadsDB
from ..stubs import TaskStatus


class UploadPartTaskDict(TypedDict):
    vault_arn: str
    vault_name: str
    file: str
    original_file_size: int
    total_parts_count: int
    sha256_of_file: str
    sha256_of_part: str
    part_offset: int
    part_size: int
    part_index: int
    upload_id: str
    save_as_path: str
    save_as_name: str


class UploadPartTask(AbstractTransferTask):

    data: UploadPartTaskDict

    def _upload_progress_callback(self, p: ReadProgressInfo):
        self.emit_transfer_progress(
            prefix="Uploading ",
            transferred=p.tell_after_read,
            planned_transfer_size=self.data['part_size']
        )

    def process(self):

        self.data = self.original_dict['data']
        if os.path.getsize(self.data['file']) != self.data['original_file_size']:
            raise RuntimeError(f"File size changed!")

        with open(self.data['file'], mode='br') as file:
            with MmapWithReadCallback(file.fileno(), access=mmap.ACCESS_READ, offset=self.data['part_offset'],
                                      length=self.data['part_size']) as mm:
                mm.callback = self._upload_progress_callback
                self.glacier.upload_archive_part(
                    vault_name=self.data['vault_name'],
                    upload_id=self.data['upload_id'],
                    part_checksum=self.data['sha256_of_part'],
                    body=typing.cast(IO[bytes], mm),
                    part_offset=self.data['part_offset'],
                    part_size=self.data['part_size']
                )

        with UploadsDB(os.path.join(self.config.workdir, "uploads.db")) as udb:
            uploaded = udb.put_upload_info(self.data['upload_id'], self.data['part_index'])
            total_parts = self.data['total_parts_count']
            if uploaded != total_parts:
                self.emit_progress(f"Uploaded part {uploaded}/{total_parts}", 0, TaskStatus.SUCCESS)
                return
            udb.delete_upload_info(self.data['upload_id'])

        archive_id = self.glacier.complete_multipart_upload(
            vault_name=self.data['vault_name'],
            upload_id=self.data['upload_id'],
            size=self.data['original_file_size'],
            archive_checksum=self.data['sha256_of_file']
        )

        inv = self.get_inventory()
        inv.put_archive(ArchiveInfo(
            archive_id=archive_id,
            parent=self.data['save_as_path'],
            name=self.data['save_as_name'],
            upload_timestamp=time.time(),
            modified_timestamp=os.path.getmtime(self.data['file']),
            sha256=self.data['sha256_of_file'],
            size=self.data['original_file_size'],
            is_dir=False
        ))
        inv.save()

        self.emit_progress("Uploaded", 0, TaskStatus.SUCCESS)

    def get_inventory(self) -> Inventory:
        inv_file = self.glacier.inventory_filename(self.data['vault_arn'])
        inv_file_full = self.config.get_inventories_location(inv_file)
        return Inventory(inv_file_full)
