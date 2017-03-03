import struct

from . import errors
from .frame import Frame
from .parser import Parser


class FrameParser(Parser):
    """Parses a stream of data in to WS frames."""

    unpack16 = struct.Struct('!H').unpack
    unpack64 = struct.Struct('!Q').unpack

    def __init__(self, frame_class=Frame):
        self._frame_class = frame_class
        super(FrameParser, self).__init__()

    def parse(self):
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
                payload_length = self.unpack16((yield self.read(2)))
            elif payload_length == 127:
                payload_length = self.unpack64((yield self.read(8)))
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
            yield frame
