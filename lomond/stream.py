"""
Parses a websocket connection.

Yields a response object followed by 0 or more Websocket messages.

"""

from __future__ import unicode_literals

import logging

from . import errors
from .frame_parser import FrameParser
from .message import Message
from .response import Response
from .utf8validator import Utf8Validator


log = logging.getLogger('lomond')


class WebsocketStream(object):
    """
    Parses a stream of data in to Headers and logical Websocket
    frames.

    """

    def __init__(self):
        self.frame_parser = FrameParser()
        self._parsed_response = False
        self._frames = []
        self._utf8_validator = Utf8Validator()

    def _validate_utf8(self, payload):
        utf8_valid, _, _, _ = self._utf8_validator.validate(payload)
        return utf8_valid

    def feed(self, data):
        """Feed in data from a socket to yield 0 or more frames."""
        # This combines fragmented frames in to a single frame
        iter_frames = iter(self.frame_parser.feed(data))

        if not self._parsed_response:
            # Process status line and headers from frame parser
            header_data = next(iter_frames, None)
            if header_data is None:
                return
            self._parsed_response = True
            yield Response(header_data)

        # Process incoming frames
        for frame in iter_frames:
            log.debug("CLI <- SRV : %r", frame)
            if frame.is_control:
                # Control messages are never fragmented
                # And may be sent in the middle of a multi-part message
                yield Message.build([frame])
            else:
                # May be fragmented
                if frame.is_continuation and not self._frames:
                    raise errors.ProtocolError(
                        'continuation frame has nothing to continue'
                    )
                if not frame.is_continuation and self._frames:
                    raise errors.ProtocolError(
                        'continuation frame expected'
                    )
                self._frames.append(frame)
                _is_text = self._frames[0].is_text
                if _is_text and not self._validate_utf8(frame.payload):
                    raise errors.CriticalProtocolError(
                        'invalid UTF-8 in text frame'
                    )
                if frame.fin:
                    yield Message.build(self._frames)
                    del self._frames[:]
                    self._utf8_validator.reset()
