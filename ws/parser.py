
class ParserEnd(Exception):
    pass

class Parser(object):

    def __init__(self):
        self._gen = None
        self._expecting = None
        self._buffer = []
        self._closed = False
        self.reset()

    def reset(self):
        self._gen = self.parse()
        self._expecting = self._gen.next()

    def feed(self, data):
        remaining = data
        while remaining:
            chunk = data[:self._expecting]
            self._buffer.append(chunk)
            self._expecting -= len(chunk)
            if not self._expecting:
                send_bytes = b''.join(self._buffer)
                del self._buffer[:]
                result = self._gen.send(send_bytes)
                if isinstance(result, int):
                    # More bytes expected
                    self._expecting = result
                else:
                    # Parsed something, yield result
                    yield result
            remaining = data[len(chunk):]

    def parse(self):
        return
        yield


if __name__ == "__main__":
    class TestParser(Parser):
        def parse(self):
            data = yield 2
            yield data
            data = yield 4
            yield data
            data = yield 3
            yield data
    parser = TestParser()

    for b in b'123456890':
        for frame in parser.feed(b):
            print(repr(frame))
