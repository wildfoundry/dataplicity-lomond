
import struct

import six

from .frame import Frame
from .parser import Parser
from .mask import mask


unpack16 = struct.Struct('!H').unpack
unpack64 = struct.Struct('!Q').unpack


class Headers(object):
    def __init__(self, header_data):
        lines = iter(header_data.split(b'\r\n'))
        self.status_line = next(lines, b'')
        self.headers = {}
        for line in lines:
            header, _colon, value = line.partition(b':')
            self.headers[header] = value


class WebsocketParser(Parser):

    def __init__(self):
        self._parse_headers = True
        self._header_data = b''

    def feed(self, data):
        if self._parse_headers:
            self._header_data += data
            if b'\r\n' in self._header_data:
                header_data, _, body = self._header_data.partition(b'\r\n\r\n')
                self._parse_headers = False
                yield Headers(header_data)
                for obj in super(WebsocketParser, self).feed(body):
                    yield obj
        else:
            for obj in super(WebsocketParser, self).feed(data):
                yield obj

    def parse(self):
        while True:
            frame = Frame.__new__()
            byte1, byte2 = bytearray((yield 2))

            frame.fin = byte1 >> 7
            frame.rsv1 = (byte1 >> 6) & 1
            frame.rsv2 = (byte1 >> 5) & 1
            frame.rsv3 = (byte1 >> 4) & 1
            frame.opcode = byte1 & 0xf

            frame.mask = byte2 >> 7
            payload_length = byte2 & 128

            if payload_length == 126:
                payload_length = unpack16((yield 2))
            elif payload_length == 127:
                payload_length = unpack64((yield 8))

            frame.payload_length = payload_length
            frame.payload_data = yield payload_length

            if frame.mask:
                masking_key = frame.masking_key = yield 4
                frame.payload_data = mask(
                    masking_key,
                    frame.payload_data
                )

            yield frame


class WebsocketStream(object):
    pass

