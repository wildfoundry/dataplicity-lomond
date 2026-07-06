from __future__ import unicode_literals

import random

from lomond.frame import Frame
from lomond.frame_parser import FrameParser
from lomond.opcode import Opcode
from lomond.parser import Parser


def _random_payload(rng, size):
    return bytes(bytearray(rng.randrange(0, 256) for _ in range(size)))


def test_frame_parser_random_roundtrip():
    rng = random.Random(1337)
    parser = FrameParser(parse_headers=False, validate=False)
    for _ in range(200):
        opcode = rng.choice([Opcode.TEXT, Opcode.BINARY, Opcode.PING, Opcode.PONG])
        size = rng.randrange(0, 200)
        if opcode in (Opcode.PING, Opcode.PONG):
            size = min(size, 125)
        if opcode == Opcode.TEXT:
            payload = bytes(bytearray(rng.randrange(32, 126) for _ in range(size)))
        else:
            payload = _random_payload(rng, size)
        frame_bytes = Frame(opcode, payload=bytearray(payload), mask=False).to_bytes()
        parsed = list(parser.feed(frame_bytes))
        frame = parsed[0]
        assert frame.opcode == opcode
        assert bytes(frame.payload) == payload


def test_parser_random_chunk_boundaries():
    class SplitParser(Parser):
        def parse(self):
            while True:
                first = yield self.read(3)
                second = yield self.read_until(b'\n')
                third = yield self.read(2)
                yield first + second + third

    rng = random.Random(7)
    source = b'ABChello world\nZZ'
    parser = SplitParser()
    pos = 0
    result = []
    while pos < len(source):
        step = rng.randrange(1, 5)
        chunk = source[pos:pos + step]
        pos += step
        for value in parser.feed(chunk):
            result.append(value)
    assert result == [source]
