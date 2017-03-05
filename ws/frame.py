"""
Manages individual Websocket frames.

A websocket 'message' may consist of several of these frames.

"""

from __future__ import print_function

import struct

import six

from . import errors
from .mask import make_masking_key, mask
from .opcode import is_reserved, is_control, Opcode


class Frame(object):

    def __init__(self, opcode, payload=b'', masking_key=None,
                 fin=1, rsv1=0, rsv2=0, rsv3=0):
        self.opcode = opcode
        self.payload = payload
        self.masking_key = masking_key
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3

        self.mask = 0
        self.validate()

    def __repr__(self):
        opcode_name = Opcode.to_str(self.opcode)
        return "<frame {} ({} bytes)>".format(
            opcode_name,
            len(self)
        )

    def __len__(self):
        return len(self.payload)

    # Use struct module to pack ws frame header
    _pack8 = struct.Struct('!BB4B').pack  # 8 bit length field
    _pack16 = struct.Struct('!BBH4B').pack  # 16 bit length field
    _pack64 = struct.Struct('!BBQ4B').pack  # 64 bit length field

    @classmethod
    def build(cls, opcode, payload=b'', fin=0, rsv1=0, rsv2=0, rsv3=0):
        """Build a WS frame header."""
        # https://tools.ietf.org/html/rfc6455#section-5.2
        masking_key = make_masking_key()
        mask_bit = 1 << 7
        byte0 = fin << 7 | rsv1 << 6 | rsv2 << 5 | rsv3 << 4 | opcode
        length = len(payload)
        if length < 126:
            header_bytes = cls._pack8(
                byte0, mask_bit | length, masking_key
            )
        elif length < (1 << 16):
            header_bytes = cls._pack16(
                byte0, mask_bit | 126, length, masking_key
            )
        elif length < (1 << 63):
            header_bytes = cls._pack64(
                byte0, mask_bit | 127, length, masking_key
            )
        else:
            # Can't send a payload > 2**63 bytes
            raise errors.FrameBuildError(
                'payload is too large for a single frame'
            )
        frame_bytes = header_bytes + mask(masking_key, payload)
        return frame_bytes

    @classmethod
    def build_binary(cls, payload):
        if not isinstance(payload, bytes):
            raise TypeError("payload should be bytes")
        return cls.build(Opcode.BINARY, payload)

    @classmethod
    def build_text(cls, payload):
        if not isinstance(payload, six.text_type):
            raise TypeError("payload should be unicode")
        return cls.build(Opcode.TEXT, payload)

    def validate(self):
        """Check the frame and raise any errors."""
        if self.is_control and len(self.payload) > 125:
            raise errors.ProtocolError(
                "Control frames must < 125 bytes in length"
            )
        if self.rsv1 or self.rsv2 or self.rsv3:
            raise errors.ProtocolError(
                "reserved bits set"
            )

        if is_reserved(self.opcode):
            raise errors.ProtocolError(
                "opcode is reserved"
            )

        if not self.fin and is_control(self.opcode):
            raise errors.ProtocolError(
                "control frames may not be fragmented"
            )

    @property
    def is_control(self):
        return self.opcode >= 8

    @property
    def is_text(self):
        return self.opcode == Opcode.TEXT

    @property
    def is_binary(self):
        return self.opcode == Opcode.BINARY

    @property
    def is_continuation(self):
        return self.opcode == Opcode.CONTINUATION

    @property
    def is_ping(self):
        return self.opcode == Opcode.PING

    @property
    def is_pong(self):
        return self.opcode == Opcode.PONG

    @property
    def is_close(self):
        return self.opcode == Opcode.CLOSE


if __name__ == "__main__":
    msg = Frame(Opcode.BINARY, b'Hello, World', fin=1)
    print(msg)