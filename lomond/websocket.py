"""
Abstract websocket functionality.

"""

from __future__ import print_function
from __future__ import unicode_literals

from base64 import b64encode
from hashlib import sha1
import logging
import os

from six.moves.urllib.parse import urlparse

from . import constants
from . import errors
from . import events
from .frame import Frame
from .opcode import Opcode
from .response import Response
from .stream import WebsocketStream
from .session import WebsocketSession
from .status import Status


log = logging.getLogger('ws')


class WebSocket(object):
    """IO independent websocket functionality."""

    def __init__(self, url, protocols=None):
        self.url = url
        self.protocols = protocols or []
        self._session = None

        self.stream = WebsocketStream()
        _url = urlparse(url)
        self.scheme = _url.scheme
        host, _, port = _url.netloc.partition(':')
        if not port:
            port = '443' if self.scheme == 'wss' else '80'
        if not port.isdigit():
            raise ValueError('illegal port value')
        port = int(port)
        self.host = host
        self.port = port
        self._host_port = "{}:{}".format(host, port)
        self.resource = _url.path or '/'
        if _url.query:
            self.resource = "{}?{}".format(host, _url.query)
        self.key = b64encode(os.urandom(16))

        self._sent_request = False
        self._running = False
        self._closing = False
        self._closed = False

    def __repr__(self):
        return "WebSocket('{}')".format(self.url)

    @property
    def session(self):
        return self._session

    def connect(self, poll=5, session_class=WebsocketSession):
        if self._running:
            raise errors.WebSocketInUse(
                "Can't connect while WebSocket is running"
            )
        self._session = WebsocketSession(self)
        self._running = True
        return self._session.events(poll=poll)

    __iter__ = connect

    def close(self, code=Status.NORMAL, reason=b'goodbye'):
        self._send_close(code, reason)
        self._closing = True

    @property
    def is_closing(self):
        return self._closing

    @property
    def is_closed(self):
        return self._closed

    def feed(self, data):
        """Feed with data from the socket."""
        session = self.session
        for message in self.stream.feed(data):
            log.debug('%r', message)
            if isinstance(message, Response):
                try:
                    yield self.on_response(message)
                except errors.HandshakeError as error:
                    yield events.Rejected(str(error))
                    break
                except Exception as error:
                    log.exception('on_response failed')
                    yield events.Rejected(str(error))
                    break
            else:
                if message.is_close:
                    if self._closing:
                        yield events.Closed(message.code, message.reason)
                        self._closed = True
                    else:
                        self.close(message.code, message.reason)
                        self._closing = True
                elif message.is_ping:
                    session.write(Opcode.PONG, message.payload)
                elif message.is_pong:
                    yield events.Pong(message)
                elif message.is_binary:
                    yield events.Binary(message)
                elif message.is_text:
                    yield events.Text(message)
                else:
                    yield events.UnknownMessage(message)

    def get_request(self):
        """Get the request (in bytes)"""
        request = [
            "GET {} HTTP/1.1".format(self.resource)
        ]
        protocols = ", ".join(self.protocols)
        version = '{}'.format(constants.WS_VERSION)
        headers = [
            ('Host', self._host_port),
            ('Upgrade', 'websocket'),
            ('Connection', 'Upgrade'),
            ('Sec-WebSocket-Protocol', protocols),
            ('Sec-WebSocket-Key', self.key),
            ('Sec-WebSocket-Version', version)
        ]
        for header, value in headers:
            request.append('{}: {}'.format(header, value).encode())
        request.append('\r\n')
        request_bytes = b'\r\n'.join(line.encode() for line in request)
        return request_bytes

    def on_response(self, response):
        """Called when the HTTP response has been received."""

        if response.status_code != 101:
            raise errors.HandshakeError(
                'Websocket upgrade failed (code={})',
                response.status_code
            )

        upgrade_header = response.get(b'upgrade', b'?').lower()
        if upgrade_header != b'websocket':
            raise errors.HandshakeError(
                "Can't upgrade to {}",
                upgrade_header.decode(errors='replace')
            )

        accept_header = response.get(b'sec-websocket-accept', None)
        if accept_header is None:
            raise errors.HandshakeError(
                "No Sec-WebSocket-Accept header"
            )

        challenge = b64encode(
            sha1(self.key + constants.WS_KEY).digest()
        )

        if accept_header.lower() != challenge.lower():
            raise errors.HandshakeError(
                "Web-WebSocket-Accept challenge failed"
            )

        protocol = response.get(b'sec-websocket-protocol')
        extensions = set(response.get_list(b'sec-websocket-extensions') or [])

        return events.Accepted(protocol, extensions)

    def send_ping(self, data):
        """Send a ping request."""
        if len(data) <= 125:
            raise ValueError('ping data should be <= 125')
        self.session.send(Opcode.PING, data)

    def send_pong(self, data):
        """Send a ping request."""
        if len(data) <= 125:
            raise ValueError('ping data should be <= 125')
        self.session.send(Opcode.PONG, data)

    def send_binary(self, data):
        """Send a binary frame."""
        self.session.send(Opcode.BINARY, data)

    def send_text(self, text):
        """Send a text frame."""
        self.session.send(Opcode.TEXT, text.encode(errors='replace'))

    def _send_close(self, code, reason):
        """Send a close frame."""
        frame_bytes = Frame.build_close_payload(code, reason)
        self.session.send(Opcode.CLOSE, frame_bytes)

    def send_request(self):
        """Send the HTTP request."""
        request = self.get_request()
        log.debug('REQUEST: %r', request)
        self.session.write(request)
        self._sent_request = True
