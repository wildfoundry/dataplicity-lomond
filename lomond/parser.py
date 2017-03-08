"""
Coroutine base stream parser.

"""

from __future__ import unicode_literals


class Parser(object):
    """
    Coroutine based stream parser.

    Splits a steam of arbitrary sequences of bytes in to logical
    objects. Essentially the `feed` method will yield any results of
    parsing.

        while True:
            data = sock.recv(1024)
            for obj in parser.feed(data):
                self.on_obj(obj)

    The coroutine magic allows parsers to be non-blocking while still
    implemented in a simple procedural manner.

    """

    def __init__(self):
        self._gen = None
        self._awaiting = None
        self._buffer = []  # Buffer for reads
        self._until = b''  # Buffer for read untils
        self._closed = False
        self.reset()

    class _Awaitable(object):
        """An operation that effectively suspends the coroutine."""
        # Analogous to Python3 asyncio concept

    class _ReadBytes(_Awaitable):
        """Reads a fixed number of bytes."""
        __slots__ = ['remaining']
        def __init__(self, count):
            self.remaining = count

    class _ReadUntil(_Awaitable):
        """Read until a separator."""
        __slots__ = ['sep']
        def __init__(self, sep):
            self.sep = sep

    read = _ReadBytes
    read_until = _ReadUntil

    def __del__(self):
        self.close()

    def reset(self):
        """Reset the parser, so it may be used on a fresh stream."""
        self._gen = self.parse()
        self._awaiting = next(self._gen)

    def close(self):
        """Close the parser."""
        if self._gen is not None:
            self._gen.close()
            self._gen = None

    def feed(self, data):
        """
        Called with data (bytes), will yield 0 or more objects parsed
        from the stream.

        """
        pos = 0
        while pos < len(data):
            # Awaiting a read of a fixed number of bytes
            if isinstance(self._awaiting, self.read):
                # This many bytes left to read
                remaining = self._awaiting.remaining
                # Bite off remaining bytes
                chunk = data[pos:pos + remaining]
                chunk_size = len(chunk)
                pos += chunk_size
                # Add to buffer
                self._buffer.append(chunk)
                remaining -= chunk_size
                if remaining:
                    # Await more bytes
                    self._awaiting = self.read(remaining)
                else:
                    # Got all the bytes we need in buffer
                    send_bytes = b''.join(self._buffer)
                    del self._buffer[:]
                    # Send to coroutine, get new 'awaitable'
                    self._awaiting = self._gen.send(send_bytes)
            # Awaiting a read until a terminator
            elif isinstance(self._awaiting, self.read_until):
                # Reading to separator
                self._until += data
                sep = self._awaiting.sep
                if sep in self._until:
                    # Found separator
                    # Get data prior to and including separator
                    split_index = self._until.index(sep) + len(sep)
                    send_bytes = self._until[:split_index]
                    # Reset data, to continue parsing
                    data = self._until[split_index:]
                    self._until = b''
                    pos = 0
                    # Send bytes to coroutine, get new 'awaitable'
                    self._awaiting = self._gen.send(send_bytes)
                else:
                    pos += len(data)
            # Yield any non-awaitables...
            while not isinstance(self._awaiting, self._Awaitable):
                yield self._awaiting
                self._awaiting = next(self._gen)


    def parse(self):
        """
        A generator to parse incoming stream.

        Yield the result of `self.read` to read n bytes from the stream.
        Yield any parsed objects

        Here's an example::

            size = struct.unpack('<I', yield self.read(4))
            data = yield self.read(size)
            yield data.decode()

        """
        return
        yield


if __name__ == "__main__":
    class TestParser(Parser):
        def parse(self):
            data = yield self.read_until(b'\r\n\r\n')
            yield data
            data = yield self.read(1)
            yield data
            data = yield self.read(2)
            yield data
            data = yield self.read(4)
            yield data
            data = yield self.read(2)
            yield data
    parser = TestParser()
    for b in (b'head', b'ers: example', b'\r\n', b'\r\n', b'12', b'34', b'5', b'678', b'', b'90'):
        for frame in parser.feed(b):
            print(repr(frame))
