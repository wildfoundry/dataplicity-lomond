"""
Parse a stream of Websocket frames, and optional HTTP headers.

"""

from __future__ import unicode_literals

import logging
import struct

from . import errors
from .frame import CompressedFrame, Frame
from .parser import Parser
from .utf8validator import Utf8Validator


log = logging.getLogger("lomond")


class FrameParser(Parser):
    """Parses a stream of data in to HTTP headers + WS frames."""

    unpack16 = struct.Struct(b"!H").unpack
    unpack64 = struct.Struct(b"!Q").unpack
    frame_class = Frame

    def __init__(self):
        self._is_text = False
        self._utf8_validator = Utf8Validator()
        super(FrameParser, self).__init__()

    def read_text(self, length):
        """Read encoded text."""
        return self.read_utf8(
            length,
            self._utf8_validator
        )

    def parse(self):
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
                (payload_length,) = self.unpack16((yield self.read(2)))
            elif payload_length == 127:
                (payload_length,) = self.unpack64((yield self.read(8)))
            if payload_length > 0x7fffffffffffffff:
                raise errors.PayloadTooLarge("payload is too large")

            if mask_bit:
                masking_key = yield self.read(4)
            else:
                masking_key = None

            frame = self.frame_class(
                opcode,
                masking_key=masking_key,
                fin=fin,
                rsv1=rsv1,
                rsv2=rsv2,
                rsv3=rsv3,
            )
            frame.validate()

            if frame.is_text:
                self._is_text = True

            if payload_length:
                _is_text_continuation = (
                    frame.is_continuation and self._is_text
                )
                if frame.is_text or _is_text_continuation:
                    frame.payload = yield self.read_text(payload_length)
                else:
                    frame.payload = yield self.read(payload_length)

            if (
                self._utf8_validator is not None
                and frame.fin
                and (frame.is_text or frame.is_continuation)
            ):
                self._utf8_validator.reset()
            if frame.fin:
                self._is_text = False

            yield frame


class CompressedFrameParser(FrameParser):
    """Specialised FrameParser for compressed frames."""

    frame_class = CompressedFrame

    def read_text(self, length):
        """Read text without validating utf-8."""
        return self.read(length)
