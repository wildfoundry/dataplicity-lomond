"""
Parse a stream of Websocket frames, and optional HTTP headers.

"""

import logging
import struct

from . import errors
from .frame import Frame
from .parser import Parser


log = logging.getLogger('ws')


class FrameParser(Parser):
    """Parses a stream of data in to HTTP headers + WS frames."""

    unpack16 = struct.Struct('!H').unpack
    unpack64 = struct.Struct('!Q').unpack

    def __init__(self, frame_class=Frame, parse_headers=True):
        self._frame_class = frame_class
        self._parse_headers = parse_headers
        super(FrameParser, self).__init__()

    def parse(self):
        # Get the HTTP headers
        if self._parse_headers:
            header_data = yield self.read_until(b'\r\n\r\n')
            log.debug('HEADERS: %r', header_data)
            yield header_data

        # Get any WS frames
        while True:
            byte1, byte2 = bytearray((yield self.read(2)))

            fin = byte1 >> 7
            rsv1 = (byte1 >> 6) & 1
            rsv2 = (byte1 >> 5) & 1
            rsv3 = (byte1 >> 4) & 1
            opcode = byte1 & 0b00001111

            mask_bit = byte2 >> 7
            payload_length = byte2 & 0b01111111

            if payload_length == 126:
                payload_length = self.unpack16((yield self.read(2)))[0]
            elif payload_length == 127:
                payload_length = self.unpack64((yield self.read(8)))[0]
            if payload_length > 0x7fffffffffffffff:
                raise errors.PayloadTooLarge("payload is too large")

            if mask_bit:
                masking_key = yield self.read(4)
            else:
                masking_key = None

            frame = self._frame_class(
                opcode,
                masking_key=masking_key,
                fin=fin,
                rsv1=rsv1,
                rsv2=rsv2,
                rsv3=rsv3
            )
            frame.payload = yield self.read(payload_length)
            log.debug('PARSED: %r', frame)
            yield frame

if __name__ == "__main__":
    data = b'\x88\x02\x03\xe8'
    parser = FrameParser(parse_headers=False)
    print(list(parser.feed(data)))
