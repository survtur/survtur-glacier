import base64
import datetime
import enum
import hashlib
import logging
import os.path
import random
import typing
import urllib.parse
from typing import Callable, Any
from typing import List, Optional, Iterator, NamedTuple, Tuple
from typing.io import IO

import boto3

from ..common.fast_glacier import to_fast_glacier, FastGlacierArchiveInfo
from ..common.helpers import MB, KB
from ..common.iopart2 import BufferedReaderWithCallback, ReadProgressInfo
from ..common.stream_retreiver import retrieve_with_progress
from .stubs.vaultdict import VaultDict

_logger = logging.getLogger(__name__)


class GlacierTier(enum.Enum):
    EXPEDITED = "Expedited"
    STANDARD = "Standard"
    BULK = "Bulk"


class PartRangeInfo(NamedTuple):
    offset: int
    length: int
    range_str: str


def _ranges(whole_size: int, part_size: int) -> Iterator[PartRangeInfo]:
    """
    Returns chunks offset, size and bytes string for parts uploading.
    (2000, 1000, 'bytes 2000-2999/*')

    :param whole_size: size in bytes
    :param part_size: size in bytes
    """
    start = 0
    while whole_size - start > part_size:
        end = start + part_size
        yield PartRangeInfo(start, part_size, f"bytes {start}-{end - 1}/*")
        start = end

    yield PartRangeInfo(start, whole_size - start, f"bytes {start}-{whole_size - 1}/*")


def vault_name_from_arn(arn: str):
    return os.path.basename(arn)


class SurvturGlacier:

    def __init__(self, access_key_id: str, secret_access_key: str, region_name: str):
        self._b = boto3.client("glacier",
                               aws_access_key_id=access_key_id,
                               aws_secret_access_key=secret_access_key,
                               region_name=region_name)

    @staticmethod
    def inventory_filename(vault_arn: str) -> str:
        sha256 = hashlib.sha256(vault_arn.encode('utf8')).digest()
        b64 = base64.urlsafe_b64encode(sha256).decode('utf8')
        safe_name = urllib.parse.quote(vault_name_from_arn(vault_arn))
        return f"{safe_name} --- {b64}.sqlite3"

    def download_vaults_list(self) -> List[VaultDict]:
        data = self._b.list_vaults()
        vaults = data['VaultList']
        return typing.cast(List[VaultDict], vaults)

    def request_vault_inventory(self, vault_name: str, output_format: str = 'JSON',
                                user_for_fast_glacier_compatibility: Optional[str] = None):
        """

        :param vault_name:
        :param output_format: "JSON" or "CSV"
        :param user_for_fast_glacier_compatibility:
            A name that used in fast-glacier job descriotion, like "USER-B2FA364B5C"
        :return:
        """
        if not user_for_fast_glacier_compatibility:
            user_for_fast_glacier_compatibility = f"USER-{random.randint(1000000,9999999)}"
        e = base64.b64encode(user_for_fast_glacier_compatibility.encode("utf8")).decode('ascii')
        return self._b.initiate_job(vaultName=vault_name,
                                    jobParameters={
                                        "Type": "inventory-retrieval",
                                        "Format": output_format,
                                        "InventoryRetrievalParameters": {
                                            "Limit": "999999999",
                                        },
                                        "Description": f"<a><b>4</b><e>{e}</e><f>0:0::0</f><g>0</g></a>"
                                    })

    def request_archive(self, vault_name: str, archive_id: str, tier: GlacierTier):
        return self._b.initiate_job(vaultName=vault_name,
                                    jobParameters={
                                        "Type": "archive-retrieval",
                                        "ArchiveId": archive_id,
                                        "Description": f"Getting {archive_id}",
                                        "Tier": tier.value
                                    })

    def get_job_output(self, vault_name: str, job_id: str,
                       bytes_range: Optional[Tuple[int, int]] = None,
                       on_read_callback: Optional[Callable[[int], Any]] = None,
                       read_size: int = 512 * KB) -> Iterator[bytes]:
        """

        :param vault_name:
        :param job_id:
        :param on_read_callback: Called while downloading with total received bytes parameter
        :param bytes_range:
        :param read_size:
        :return:
        """
        extra_params = {}
        if bytes_range:
            extra_params['range'] = f'bytes={bytes_range[0]}-{bytes_range[1]}'
        response = self._b.get_job_output(vaultName=vault_name, jobId=job_id, **extra_params)
        for b in retrieve_with_progress(response['body'], on_read_callback, read_size):
            yield b

    def initiate_archive_upload(self, *, file: str, vault_name: str, save_as: Optional[str] = None,
                                use_glacier_format: bool = True,
                                part_size_mb: int) -> str:

        part_size = part_size_mb * MB

        description = self._make_archive_description(file, save_as, use_glacier_format)

        response = self._b.initiate_multipart_upload(
            vaultName=vault_name,
            archiveDescription=description,
            partSize=str(part_size)
        )

        upload_id = response['uploadId']
        return upload_id

    def describe_job(self, vault_name: str, job_id: str):
        return self._b.describe_job(vaultName=vault_name, jobId=job_id)

    def upload_archive_part(self, *, vault_name: str, upload_id: str, part_checksum: str,
                            body: IO[bytes], part_offset: int, part_size: int) -> str:
        """
        Returns AWS calculated sha256TreeHash of uploaded part.
        It is the same as `part_checksum` parameter.
        """
        range_str = f"bytes {part_offset}-{part_offset + part_size - 1}/*"
        result = self._b.upload_multipart_part(
            vaultName=vault_name,
            uploadId=upload_id,
            checksum=part_checksum,
            range=range_str,
            body=body,
        )
        return result['checksum']

    def complete_multipart_upload(self, vault_name: str, upload_id: str, size: int, archive_checksum: str) -> str:
        """
        Returns AWS calculated sha256TreeHash of whole archive.
        It is the same as `archive_checksum` parameter.
        """
        result = self._b.complete_multipart_upload(
            vaultName=vault_name,
            uploadId=upload_id,
            archiveSize=str(size),
            checksum=archive_checksum,
        )
        return result['archiveId']

    def upload_archive(self, *, vault_name: str, file: str,
                       checksum: str,
                       save_name: Optional[str] = None,
                       use_glacier_format: bool = True,
                       progress_cb: Optional[Callable[[ReadProgressInfo], Any]] = None
                       ) -> str:
        """
        :return: ArchiveId
        """

        archive_description = self._make_archive_description(file, save_name, use_glacier_format)
        _logger.debug(f"Archive description: {repr(archive_description)}")
        with BufferedReaderWithCallback(open(file, mode='br'), progress_cb) as b:
            result = self._b.upload_archive(
                vaultName=vault_name,
                archiveDescription=archive_description,
                checksum=checksum,
                body=b
            )

        return result['archiveId']

    @staticmethod
    def _make_archive_description(file: str, save_as: str, use_glacier_format: bool) -> str:
        """

        :param file: local file

        :param save_as:
        :param use_glacier_format:
            If False, `save_as` will be used as archive_description.

            If True, glacier formatted description will be generated, where `save_as` is a virtual path.
            For virtual folder: "FOLDER/SUBFOLDER/"
            For files: "FOLDER/SUBFOLDER/file.zip"
            Notice that last slash defines is it file or directory.
        """
        if not save_as:
            save_as = os.path.basename(file)
        if use_glacier_format:
            try:
                lm = datetime.datetime.fromtimestamp(os.path.getmtime(file))
            except FileNotFoundError:
                lm = datetime.datetime.now()

            f = FastGlacierArchiveInfo(
                parent='',
                name=save_as,
                is_dir=save_as.endswith("/"),
                last_modified=lm
            )
            archive_description = to_fast_glacier(f)
        else:
            archive_description = save_as
        return archive_description
