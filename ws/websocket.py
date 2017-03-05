from __future__ import unicode_literals

from base64 import b64encode
from hashlib import sha1
import logging
import os
from urllib2 import urlparse

from six.moves import urlparse

from . import constants
from .import errors
from .stream import WebsocketStream


log = logging.getLogger('ws')


class WebSocketBase(object):
    """IO independent websocket functionality."""

    def __init__(self, url, protocols=None):
        self.url = url
        self.protocols = protocols or []

        self.stream = WebsocketStream()
        self._response = None
        _url = urlparse.urlparse(url)
        self.scheme = _url.scheme
        host, port = _url.netloc.partition(':')
        self.host = host
        self.port = port
        self.resource = '/' or _url.path
        if _url.query:
            self.resource = "{}?{}".format(_url.query)
        self.key = b64encode(os.urandom(16))
        self._closed = False

    def feed(self, data):
        iter_stream = iter(self.stream.feed(data))
        if self._response is None:
            response = self._response = next(iter_stream, None)
            if response is not None:
                self.on_response(response)
        for message in iter_stream:
            self._on_message(message)

    def _build_request(self):
        """Build the WS upgrade request."""
        request = [
            "GET HTTP/1.1 {}".format(self.resource)
        ]
        protocols = ", ".join(self.protocols)
        version = '{}'.format(constants.WS_VERSION)
        headers = [
            ('Upgrade', 'websocket'),
            ('Connection', 'Upgrade'),
            ('Sec-WebSocket-Protocol', protocols),
            ('Sec-WebSocket-Key', self.key),
            ('Sec-WebSocket-Version', version)
        ]
        for header, value in headers:
            request.append('{}: {}'.format(header, value).encode())
        request.append('')
        request_bytes = b'\r\n'.join(line.encode() for line in request)
        return request_bytes

    def on_response(self, response):
        if response.status_code != 101:
            raise errors.HandshakeError(
                'Websocket upgrade failed (code={})',
                response.status_code
            )

        upgrade_header = response.get(b'upgrade', b'?')
        if upgrade_header != b'websocket':
            raise errors.HandshakeError(
                "Can't upgrade to {}",
                upgrade_header.decode(error='replace')
            )

        accept_header = response.get(b'sec-websocket-accept', None)
        if accept_header is None:
            raise errors.HandshakeError(
                "No Sec-WebSocket-Accept header"
            )
        challenge = b64encode(
            sha1(self.key + constants.WS_KEY).digest()
        ).lower()
        if accept_header != challenge:
            raise errors.HandshakeError(
                "Web-WebSocket-Accept challenge failed"
            )

        self.server_protocols = response.get_list(b'sec-websocket-protocol')
        self.server_extensions = response.get_list(b'sec-websocket-extensions')


    def _on_message(message):
        """Called with new messages, to trap errors."""
        try:
            return self.on_message(message)
        except:
            log.exception("error in on_message")


    def on_message(message):
        pass


    def on_ping(message):
        pass


    def on_pong(message):
        pass