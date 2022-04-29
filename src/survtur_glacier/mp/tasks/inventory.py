import csv
import logging
import os
import time
from datetime import datetime
from typing import TypedDict

from ...common.fast_glacier import from_fast_glacier
from ...common.helpers import date_string_to_date
from ...common.stream_line_reader import BytesToLinesIterator
from ...glacier.inventory import Inventory, ArchiveInfo
from ...glacier.stubs.archive import Archive
from . import id_gen
from .abstract import AbstractTask, AbstractTransferTask
from ..stubs import TaskStatus, CommonTaskDict, TaskMetaDict, TaskType, TaskCategory, TaskPriority

_logger = logging.getLogger(__name__)


class InitiateInventoryRequestTaskDataDict(TypedDict):
    vault_arn: str
    vault_name: str
    format: str


class InitiateInventoryRequestTask(AbstractTask):

    def process(self):
        data: InitiateInventoryRequestTaskDataDict = self.original_dict['data']

        # Sending request to create inventory
        self.emit_progress('Requesting…', 0)
        output = self.glacier.request_vault_inventory(data['vault_name'], output_format=data['format'],
                                                      user_for_fast_glacier_compatibility=self.config.client_id)
        job_id = output['jobId']

        # Creating task to check if inventory ready and download it after 3600 seconds
        new_meta = TaskMetaDict(
            id=id_gen.task_id(),
            group_id=id_gen.group_id(""),
            name=self.original_dict['meta']['name'],
            type=TaskType.INVENTORY_RECEIVE,
            priority=TaskPriority.META,
            start_after=int(time.time()) + 3600*4,
            created=self.original_dict['meta']['created'],
            category=TaskCategory.META
        )
        new_data: RetrieveInventoryContentTaskDataDict = {
            "job_id": job_id,
            "vault_name": data['vault_name'],
            "vault_arn": data['vault_arn']
        }

        t: CommonTaskDict = {'meta': new_meta, 'data': new_data}
        self.queue_of_tasks_to_be_added.put(t)
        self.emit_progress('', 0, TaskStatus.REMOVED_SILENTLY)


class RetrieveInventoryContentTaskDataDict(TypedDict):
    job_id: str
    vault_name: str
    vault_arn: str


def _archive_from_aws_dict(d: Archive) -> ArchiveInfo:
    try:
        a = _parse_fast_glacier(d)
        return a
    except Exception as e:
        _logger.exception(e)
        pass

    a = ArchiveInfo(
        archive_id=d['ArchiveId'],
        parent="",
        name=d['ArchiveDescription'],
        upload_timestamp=date_string_to_date(d['CreationDate']).timestamp(),
        modified_timestamp=None,
        sha256=d['SHA256TreeHash'],
        size=d['Size'],
        is_dir=False
    )
    return a

def _parse_fast_glacier(d: Archive) -> ArchiveInfo:
    info = from_fast_glacier(d['ArchiveDescription'])
    a = ArchiveInfo(
        archive_id=d['ArchiveId'],
        parent=info.parent,
        name=info.name,
        upload_timestamp=date_string_to_date(d['CreationDate']).timestamp(),
        modified_timestamp=info.last_modified.timestamp(),
        sha256=d['SHA256TreeHash'],
        size=d['Size'] if not info.is_dir else None,
        is_dir=info.is_dir
    )
    return a


class RetrieveInventoryContentTask(AbstractTransferTask):
    data: RetrieveInventoryContentTaskDataDict
    percent: int = 0
    inventory_size: int

    def process(self):
        self.data = self.original_dict['data']
        self.check_job(self.data['vault_name'], self.data['job_id'], self._download_inventory, retry_delay=3600)

    def transfer_callback(self, bytes_received: int):
        self.emit_transfer_progress(bytes_received, "", planned_transfer_size=self.inventory_size)

    def _download_inventory(self, job_info: dict):
        db_filename = self.glacier.inventory_filename(self.data['vault_arn'])
        db_fullpath = self.config.get_inventories_location(db_filename)
        self.inventory_size = job_info['InventorySizeInBytes']
        inventory_getter = self.glacier.get_job_output(vault_name=self.data['vault_name'],
                                                       job_id=self.data['job_id'],
                                                       on_read_callback=self.transfer_callback)

        inv = Inventory(db_fullpath)

        inv.clear()
        inv.set_vault_info(self.data['vault_arn'], datetime.now().timestamp())
        cvs_reader = csv.DictReader((b.decode('ascii') for b in BytesToLinesIterator(inventory_getter)))
        temp_db = db_fullpath + ".temp_data"
        with open(temp_db, mode='tw') as f:
            for d in cvs_reader:
                print(d, file=f)
                inv.put_archive(_archive_from_aws_dict(d))

        inv.save()
        os.remove(temp_db)

        self.emit_progress('Inventory updated', 0, TaskStatus.SUCCESS)
