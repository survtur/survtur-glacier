import mmap
from io import BytesIO, BufferedReader
from typing import BinaryIO, NamedTuple, Any, Callable, Optional


class ReadProgressInfo(NamedTuple):
    tell_after_read: int
    read: int
    total_read: int


class BytesIOWithCallback(BytesIO):

    def __init__(self, buf: bytes,
                 callback: Callable[[ReadProgressInfo], Any]):
        self._callback = callback
        self._total_read = 0
        super().__init__(buf)

    def read(self, n=-1):
        chunk = super().read(n)
        self._total_read += len(chunk)
        if self._callback:
            self._callback(ReadProgressInfo(self.tell(), len(chunk), self._total_read))
        return chunk


class BufferedReaderWithCallback(BufferedReader):
    """
    Works with opened binary files
    """

    def __init__(self, raw: BinaryIO,
                 callback: Callable[[ReadProgressInfo], Any]):
        self._callback = callback
        self._total_read = 0

        # noinspection PyTypeChecker
        super().__init__(raw)

    def read(self, n=-1):
        chunk = super().read(n)
        self._total_read += len(chunk)
        if self._callback:
            self._callback(ReadProgressInfo(self.tell(), len(chunk), self._total_read))
        return chunk


class MmapWithReadCallback(mmap.mmap):

    callback: Optional[Callable[[ReadProgressInfo], Any]] = None
    total_read: int = 0

    def read(self, n: Optional[int] = None) -> bytes:
        data = super().read(n)
        if self.callback:
            read_now = len(data)
            self.total_read += read_now
            r = ReadProgressInfo(self.tell(), read=read_now, total_read=self.total_read)
            self.callback(r)
        return data
