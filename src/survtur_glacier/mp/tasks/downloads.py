import logging
import os.path
import time
from typing import TypedDict, NamedTuple, Dict, List

from ...common.helpers import MB
from ...glacier.hasher import sha256_tree_hash_hex
from ...glacier.survtur_glacier import GlacierTier
from . import id_gen
from .abstract import AbstractTask, AbstractTransferTask
from .errors import BadHash
from ..stubs import TaskStatus, CommonTaskDict, TaskMetaDict, TaskType, TaskCategory, TaskPriority

_logger = logging.getLogger(__name__)


class InitiateArchiveRequestTaskDataDict(TypedDict):
    vault_name: str
    archive_id: str
    save_dir: str
    save_name: str
    dirs_to_create: List[str]
    hash: str
    tier: str


class RetrieveArchiveTaskDataDict(TypedDict):
    vault_name: str
    job_id: str
    save_dir: str
    save_name: str
    dirs_to_create: List[str]
    hash: str
    tier: str  # Used to set proper delay between retries


class _Delay(NamedTuple):
    initial: int
    retry: int


_tier_delays: Dict[GlacierTier, _Delay] = {
    GlacierTier.EXPEDITED: _Delay(180, 180),
    GlacierTier.STANDARD: _Delay(4 * 3600, 2 * 3600),
    GlacierTier.BULK: _Delay(6 * 3600, 3 * 3600),
}


class InitiateArchiveRequestTask(AbstractTask):

    def process(self):
        data: InitiateArchiveRequestTaskDataDict = self.original_dict['data']

        self.emit_progress('Requesting…', 0)
        tier = GlacierTier(data['tier'])

        output = self.glacier.request_archive(data['vault_name'], data['archive_id'], tier)
        job_id = output['jobId']

        new_meta = TaskMetaDict(id=id_gen.task_id(),
                                group_id=id_gen.group_id(""),
                                name=self.original_dict['meta']['name'],
                                type=TaskType.ARCHIVE_RECEIVE,
                                priority=TaskPriority.DOWNLOAD_FILE,
                                start_after=int(time.time()) + _tier_delays[tier].initial,
                                created=self.original_dict['meta']['created'],
                                category=TaskCategory.DOWNLOAD)

        new_data = RetrieveArchiveTaskDataDict(
            vault_name=data['vault_name'],
            job_id=job_id,
            save_dir=data['save_dir'],
            save_name=data['save_name'],
            dirs_to_create=data['dirs_to_create'],
            hash=data['hash'],
            tier=data['tier']
        )

        t: CommonTaskDict = {'meta': new_meta, 'data': new_data}
        self.queue_of_tasks_to_be_added.put(t)
        self.emit_progress('', 0, TaskStatus.REMOVED_SILENTLY)


class ReceiveArchiveTask(AbstractTransferTask):
    percent: int = 0
    data: RetrieveArchiveTaskDataDict
    archive_size_in_bytes: int

    def process(self):
        self.data = self.original_dict['data']
        tier = GlacierTier(self.data['tier'])
        next_check_delay = _tier_delays[tier].retry
        if self.data['job_id'] == "FAKE":
            raise NotImplementedError

        self.check_job(self.data['vault_name'], self.data['job_id'], self._download_archive, next_check_delay)

    def _download_archive(self, job_info: dict):

        assert os.path.isdir(self.data['save_dir'])

        save_dir = self.data['save_dir']
        for dir_name in self.data['dirs_to_create']:
            save_dir = os.path.join(save_dir, dir_name)
            if not os.path.isdir(save_dir):
                os.mkdir(save_dir)

        save_file = os.path.join(save_dir, self.data['save_name'])
        assert not os.path.exists(save_file)

        self.archive_size_in_bytes = job_info['ArchiveSizeInBytes']
        temp_file = save_file + ".tmp"
        if os.path.exists(temp_file):
            self.start_download_from = os.path.getsize(temp_file)
            start_percent = (self.start_download_from / self.archive_size_in_bytes) * 100
            _logger.info(f"Resuming download from {self.start_download_from} / {start_percent:0.1f}%")
        else:
            self.start_download_from = 0
            _logger.info("Nothing to resume. Start downloading from the beginning.")

        with open(temp_file, mode='ba') as f:
            body_flow = self.glacier.get_job_output(
                vault_name=self.data['vault_name'],
                job_id=self.data['job_id'],
                bytes_range=(self.start_download_from, self.archive_size_in_bytes - 1),
                on_read_callback=self.emit_download_progress_plus,
                read_size=1 * MB
            )

            for b in body_flow:
                f.write(b)

        with open(temp_file, mode='br') as f:
            sha, _ = sha256_tree_hash_hex(f, 256, progress_cb=self.sha_progress)
        if sha == self.data['hash']:
            _logger.info("Hash is ok")
        else:
            new_name = save_file + f".badHash.{int(time.time())}"
            _logger.critical(f"Incorrect hash! Bad file saved to {new_name}")
            os.renames(temp_file, new_name)
            raise BadHash

        os.renames(temp_file, save_file)
        self.emit_progress("Saved", 0, TaskStatus.SUCCESS)

    def sha_progress(self, total_bytes_read: int):
        self.emit_transfer_progress(total_bytes_read, "Checking", self.archive_size_in_bytes)

    def emit_download_progress_plus(self, i: int):
        self.emit_transfer_progress(self.start_download_from + i, "Downloading ", self.archive_size_in_bytes)
