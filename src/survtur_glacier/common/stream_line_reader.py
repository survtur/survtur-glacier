class BytesToLinesIterator:
    """
    It reads bytes iterator and yields lines
    """

    def __init__(self, bytes_iterator):
        self._bytes_iterator = bytes_iterator
        self._buf = bytearray()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.read_line()
        if line:
            return line
        raise StopIteration

    def read_line(self):
        eof = False
        while True:
            index = self._buf.find(b'\n')
            if index != -1:
                data = self._buf[:index + 1]
                self._buf[:index + 1] = b''
                return data

            if eof:
                if len(self._buf) != 0:
                    data = self._buf[:]
                    self._buf[:] = b''
                    return data
                else:
                    return b''
            try:
                more_data = next(self._bytes_iterator)
                self._buf.extend(more_data)
            except StopIteration:
                eof = True

    def __len__(self):
        return len(self._buf)
