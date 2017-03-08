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
            # Process status line and headers from frame parser
            header_data = next(iter_frames, None)
            if header_data is None:
                return
            self._parsed_response = True
            yield Response(header_data)

        # Process incoming frames
        for frame in iter_frames:
            if frame.is_control:
                # Control messages are never fragmented
                # And may be sent in the middle of a multi-part message
                yield Message.build([frame])
            else:
                # May be fragmented
                self._frames.append(frame)
                if frame.fin:
                    # Combine any multi part frames in to a single
                    # Message
                    yield Message.build(self._frames)
                    del self._frames[:]
