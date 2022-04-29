import hashlib
import logging
from io import BytesIO
from itertools import zip_longest
from typing import Tuple, List, Optional, Callable, Any, Union
from typing.io import BinaryIO

from ..common.helpers import is_power_of_two, MB

_logger = logging.getLogger(__name__)


def sha256_tree_hash_hex(readable_io: Union[BinaryIO, BytesIO], chunk_size_mb: int,
                         progress_cb: Optional[Callable[[int], Any]] = None) -> Tuple[str, Tuple[str]]:
    """
    :param readable_io:
    :param chunk_size_mb: Note, this is in megabytes, not just bytes.
    :param progress_cb: callback that emit progress in total bytes read.
    :return: tree_hash of whole file and hashes of its chunks
    """
    if chunk_size_mb > 65536:
        _logger.warning(f"Looks like chunk size is too big [{chunk_size_mb} MB]. Maybe you provided size in bytes?")
    one, many = sha256_tree_hash(readable_io, chunk_size_mb, progress_cb)
    return one.hex(), tuple((h.hex() for h in many))


def sha256_tree_hash(readable_io: Union[BinaryIO, BytesIO], chunk_size_mb: int,
                     progress_cb: Optional[Callable[[int], Any]] = None) -> Tuple[bytes, Tuple[bytes]]:
    """
    Returns tree_hash of whole file and hashes of its chunks
    :param readable_io:
    :param progress_cb: callback that emit progress in total bytes read.
    :param chunk_size_mb:
    :return:
    """

    assert is_power_of_two(chunk_size_mb)

    _logger.debug(f"Calculating hash of {readable_io}")

    this_chunk_hashes: List[bytes] = []
    all_hashes: List[bytes] = []
    total_bytes_read = 0
    readable_io.seek(0)

    while True:

        b = readable_io.read(MB)
        total_bytes_read += len(b)

        if progress_cb:
            progress_cb(total_bytes_read)

        if not b:
            break

        this_chunk_hashes.append(hashlib.sha256(b).digest())
        if len(this_chunk_hashes) == chunk_size_mb:
            all_hashes.append(_tree_hash_of_hashes(this_chunk_hashes))
            this_chunk_hashes = []

    if this_chunk_hashes:
        all_hashes.append(_tree_hash_of_hashes(this_chunk_hashes))

    if total_bytes_read == 0:
        all_hashes = [hashlib.sha256(b'').digest()]

    return _tree_hash_of_hashes(all_hashes), tuple(all_hashes)


def _tree_hash_of_hashes(hashes: List[bytes]) -> bytes:
    while len(hashes) > 1:
        hashes = _tree_hash_of_hashes_iteration(hashes)
    return hashes[0]


def _tree_hash_of_hashes_iteration(hashes: List[bytes]) -> List[bytes]:
    output = []
    for h1, h2 in zip_longest(hashes[::2], hashes[1::2]):
        if h2 is None:
            output.append(h1)
        else:
            output.append(hashlib.sha256(h1 + h2).digest())

    return output
