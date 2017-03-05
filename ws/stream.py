from __future__ import unicode_literals

from .frame_parser import FrameParser
from .message import Message
from .response import Response


class WebsocketStream(object):
    """
    Parses a stream of data in to Headers and logical Websocket
    frames.

    """

    def __init__(self):
        self.frame_parser = FrameParser()
        self._parsed_response = False
        self._frames = []

    def feed(self, data):
        """Feed in data from a socket to yield 0 or more frames."""
        # This combines fragmented frames in to a single frame
        iter_frames = iter(self.frame_parser.feed(data))

        if not self._parsed_response:
            header_data = next(iter_frames, None)
            if header_data is not None:
                self._parsed_response = True
                yield Response(header_data)
            else:
                return

        for frame in iter_frames:
            self._frames.append(frame)
            if frame.fin:
                yield Message.build(self._frames)
                del self._frames[:]
