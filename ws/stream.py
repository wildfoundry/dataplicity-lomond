from __future__ import unicode_literals

from collections import defaultdict, OrderedDict

from .frame import FrameParser


class Headers(object):
    def __init__(self, header_data):
        lines = iter(header_data.split(b'\r\n'))
        status_line = next(lines, b'')
        tokens = iter(status_line.split(None, 3))
        self.http_ver = next(tokens, b'')
        try:
            self.status_code = int(next(tokens, b''))
        except ValueError:
            self.status_code = None
        self.status = next(tokens, b'')

        headers = defaultdict(list)
        for line in lines:
            header, _, value = line.partition(b':')
            header = header.decode(errors='replace')
            value = value.decode(errors='replace')
            headers[header].append(value)

        self._headers = {
            header: ','.join(value)
            for header, value in headers.items()
        }

    def __repr__(self):
        text = [
            "{} {} {}".format(
                self.http_ver,
                self.status_code,
                self.status
            )
        ]
        for header, value in self._headers.items():
            text.append("{}:{}".format(header, value))
        return '\n'.join(text)


    def get_header(self, name, default=None):
        return self._headers.get(name, default)


class FrameStream(object):
    """Parses a stream of data in to logical Websocket frames"""

    def __init__(self):
        self.frame_parser = FrameParser()
        self.continuation_frame = None

    def feed(self, data):
        """Feed in data from a socket to yield 0 or more frames."""
        # This combines fragmented frames in to a single frame
        for frame in self.frame_parser.feed(data):
            if frame.is_continuation:
                yield self.continuation_frame
                self.continuation_frame = None
            else:
                if frame.fin:
                    yield frame
                else:
                    if self.continuation_frame is None:
                        self.continuation_frame = frame
                    else:
                        self.continuation_frame.extend(frame)


class WebsocketStream(object):
    """Parses socket data in to headers + frames."""

    def __init__(self):
        self.websocket_stream = FrameStream()
        self._parse_headers = True
        self._header_data = b''

    def feed(self, data):
        """Yield header data, then a stream of logical WS frames."""
        if self._parse_headers:
            self._header_data += data
            if b'\r\n' in self._header_data:
                header_data, _, data = self._header_data.partition(b'\r\n\r\n')
                self._parse_headers = False
                yield Headers(header_data)
                del self._header_data
            else:
                return
        else:
            for frame in self.websocket_stream.feed(data):
                yield frame
