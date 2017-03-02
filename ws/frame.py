from __future__ import print_function

import struct

import six

from .errors import FrameBuildError
from .mask import make_masking_key, mask
from.parser import Parser


class Opcode(object):
    continuation = 0
    text = 1
    binary = 2
    reserved1 = 3
    reserved2 = 4
    reserved3 = 5
    reserved4 = 6
    reserved5 = 7
    close = 8
    ping = 9
    pong = 0xA
    reserved6 = 0xB
    reserved7 = 0xC
    reserved8 = 0xD
    reserved9 = 0xE
    reserved10 = 0xF


class FrameParser(Parser):
    """Parses a stream of data in to WS frames."""

    unpack16 = struct.Struct('!H').unpack
    unpack64 = struct.Struct('!Q').unpack

    def parse(self):
        while True:
            frame = Frame.blank()
            byte1, byte2 = bytearray((yield self.read(2)))

            frame.fin = byte1 >> 7
            frame.rsv1 = (byte1 >> 6) & 1
            frame.rsv2 = (byte1 >> 5) & 1
            frame.rsv3 = (byte1 >> 4) & 1
            frame.opcode = byte1 & 0xf

            frame.mask = byte2 >> 7
            payload_length = byte2 & 127

            if payload_length == 126:
                payload_length = self.unpack16((yield self.read(2)))
            elif payload_length == 127:
                payload_length = self.unpack64((yield self.read(8)))

            frame.payload_length = payload_length

            if frame.mask:
                masking_key = frame.masking_key = yield self.read(4)
                frame.payload_data = mask(
                    masking_key,
                    frame.payload_data
                )

            frame.payload_data = yield self.read(payload_length)

            yield frame


class Frame(object):

    def __init__(self, opcode, payload=b'', masking_key=None, fin=0, rsv1=0, rsv2=0, rsv3=0):
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv2 = rsv3
        self.opcode = opcode
        self.mask = 0
        self.payload_length = len(payload)
        self.masking_key = masking_key
        self.payload_data = payload
        self._text = None

    @classmethod
    def blank(cls):
        frame = cls.__new__()
        frame._text = None
        return frame

    # Use struct module to pack ws frame header
    _pack8 = struct.Struct('!BB4B').pack
    _pack16 = struct.Struct('!BBH4B').pack
    _pack64 = struct.Struct('!BBQ4B').pack

    @classmethod
    def build(cls, opcode, payload=b'', fin=0):
        """Build a WS frame header."""
        # https://tools.ietf.org/html/rfc6455#section-5.2
        masking_key = make_masking_key()
        mask_bit = 1 << 7
        byte0 = (fin << 7) | opcode
        length = len(payload)
        if length < 126:
            header_bytes = cls._pack8(byte0, mask_bit | length, masking_key)
        elif length < (1 << 16):
            header_bytes = cls._pack16(byte0, mask_bit | 126, length, masking_key)
        elif length < (1 << 63):
            header_bytes = cls._pack64(byte0, mask_bit | 127, length, masking_key)
        else:
            # Can't send a payload > 2**63 bytes
            raise FrameBuildError(
                'payload is too large for a single frame'
            )
        return header_bytes + payload

    @classmethod
    def build_binary(cls, payload):
        if not isinstance(payload, bytes):
            raise TypeError("payload should be bytes")
        return cls.build(Opcode.binary, payload)

    @classmethod
    def build_text(cls, payload):
        if not isinstance(payload, six.text_type):
            raise TypeError("payload should be unicode")
        return cls.build(Opcode.text, payload)

    def extend(self, frame):
        """Extend data from continuation."""
        self.payload_data += frame.data
        self.payload_length = len(self.payload_data)
        self._text = None

    @property
    def text(self):
        if self._text is None:
            self._text = self.payload_data.decode()
        return self._text

    @property
    def is_control(self):
        return self.opcode >= 8

    @property
    def is_binary(self):
        return self.opcode == Opcode.binary

    @property
    def is_text(self):
        return self.opcode == Opcode.text

    @property
    def is_continuation(self):
        return self.opcode == Opcode.continuation

    @property
    def is_ping(self):
        return self.opcode == Opcode.ping

    @property
    def is_pong(self):
        return self.opcode == Opcode.pong

    @property
    def is_close(self):
        return self.opcode == Opcode.close
