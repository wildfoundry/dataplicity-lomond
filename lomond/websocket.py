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
from .opcode import Opcode
from .response import Response
from .stream import WebsocketStream


log = logging.getLogger('ws')


class WebSocket(object):
    """IO independent websocket functionality."""

    def __init__(self, url, protocols=None):
        self.url = url
        self.protocols = protocols or []

        self.stream = WebsocketStream()
        _url = urlparse(url)
        self.scheme = _url.scheme
        host, _, port = _url.netloc.partition(':')
        if not port:
            host = '443' if self.scheme == 'wss' else '80'
        if not port.isdigit():
            raise ValueError('illegal port value')
        port = int(port)
        self.host = host
        self.port = port
        self._host_port = "{}:{}".format(host, port)
        self.resource = '/' or _url.path
        if _url.query:
            self.resource = "{}?{}".format(host, _url.query)
        self.key = b64encode(os.urandom(16))
        self._closed = False

    def __repr__(self):
        return "WebSocket({!r})".format(self.url)

    def connect(self):
        from .session import WebsocketSession
        return WebsocketSession(self)

    def feed(self, data, session):
        """Feed with data from the socket."""
        for message in self.stream.feed(data):
            log.debug('%r', message)
            if isinstance(message, Response):
                yield self.on_response(message)
            else:
                if message.is_close:
                    session.on_close_message(message)
                elif message.is_ping:
                    session.write(Opcode.PONG, message.payload)
                elif message.is_pong:
                    pass
                elif message.is_binary:
                    yield events.AppMessage(message)
                elif message.is_text:
                    yield events.AppMessage(message)
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
