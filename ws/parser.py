
class ParserEnd(Exception):
    pass


class _ReadBytes(int):
    """Tells the feed method that more bytes are required."""


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
        self._expecting = None
        self._buffer = []
        self._closed = False
        self.reset()
        self.read = _ReadBytes

    def __del__(self):
        self.close()

    def reset(self):
        """Reset the parser, so it may be used on a fresh stream."""
        self._gen = self.parse()
        self._expecting = self._gen.next()

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
        remaining = data
        while remaining:
            chunk = data[:self._expecting]
            chunk_size = len(chunk)
            remaining = data[chunk_size:]
            self._buffer.append(chunk)
            self._expecting -= chunk_size
            if not self._expecting:
                send_bytes = b''.join(self._buffer)
                del self._buffer[:]
                result = self._gen.send(send_bytes)
                if isinstance(result, _ReadBytes):
                    # More bytes expected
                    self._expecting = int(result)
                else:
                    # Parsed something, yield result
                    yield result

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
            data = yield self.read(2)
            yield data
            data = yield self.read(4)
            yield data
            data = yield self.read(3)
            yield data
    parser = TestParser()

    for b in b'123456890':
        for frame in parser.feed(b):
            print(repr(frame))
