from datetime import datetime
from typing import Iterator, Any, Optional, Callable, Union

from ..common.helpers import KB


def retrieve_with_progress(body_stream,
                           on_read_callback: Optional[Callable[[int], Any]],
                           interval: Union[int, float] = 0.2,
                           read_size: int = 512*KB) -> Iterator[bytes]:
    """
    Sequentially read body_stream. Each `interval` of seconds calls `on_read_callback(total_read_bytes)`.
    :param body_stream: Stream to read
    :param on_read_callback:
    :param interval: Min interval between progress callbacks.
    :param read_size: Size of a read iteration
    :return:
    """

    if on_read_callback:
        on_read_callback(0)

    total_read = 0
    last_progress = datetime.now()

    while True:
        read = body_stream.read(read_size)
        yield read
        if not read:
            break
        total_read += len(read)
        if on_read_callback:
            now = datetime.now()
            if (now - last_progress).total_seconds() > interval:
                on_read_callback(total_read)
                last_progress = now

    if on_read_callback:
        on_read_callback(total_read)
