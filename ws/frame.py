from __future__ import print_function

import struct

import six

from . import errors
from .mask import make_masking_key, mask
from .opcode import is_reserved, is_control, Opcode


class Frame(object):

    def __init__(self, opcode, payload=b'', masking_key=None, fin=0, rsv1=0, rsv2=0, rsv3=0):
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask = 0
        self.masking_key = masking_key
        self._payload_data = payload
        self._payload = None
        self._text = None
        self.validate()

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
            raise errors.FrameBuildError(
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

    @property
    def payload(self):
        if self._payload is None:
            if self.masking_key is None:
                self._payload = self._payload_data
            else:
                self._payload = mask(
                    self.masking_key,
                    self._payload_data
                )
        return self._payload

    @payload.setter
    def payload(self, data):
        if self.is_control and len(data) > 125:
            raise errors.ProtocolError(
                "Control frames must < 125 bytes in length"
            )
        self._payload_data = data

    def extend(self, frame):
        """Extend data from continuation."""
        self._payload_data += frame.data
        self._payload = None
        self._text = None

    def validate(self):
        """Check the frame and raise any errors."""
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
    def binary(self):
        """Get binary payload."""
        return self._payload_data

    @property
    def text(self):
        """Get decoded text."""
        if self._text is None:
            self._text = self.payload.decode()
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
