from __future__ import unicode_literals

from base64 import b64encode
import logging
import os
from urllib2 import urlparse

from six.moves import urlparse

from . import constants
from .stream import WebsocketStream


log = logging.getLogger('ws')


class WebSocketBase(object):
    """IO independent websocket functionality."""

    def __init__(self, url, protocols=None):
        self.url = url
        self.protocols = protocols or []

        self.stream = WebsocketStream()
        self._headers = None
        _url = urlparse.urlparse(url)
        self.scheme = _url.scheme
        host, port = _url.netloc.partition(':')
        self.host = host
        self.port = port
        self.resource = '/' or _url.path
        if _url.query:
            self.resource = "{}?{}".format(_url.query)
        self._key = b64encode(os.urandom(16))

    def feed(self, data):
        iter_stream = iter(self.stream.feed(data))
        if self._headers is None:
            headers = self._headers = next(iter_stream, None)
            if headers is not None:
                self._on_headers(headers)
        for message in iter_stream:
            self._on_message(message)

    def _build_request(self):
        """Build the WS upgrade request."""
        request = [
            "GET {} HTTP/1.1".format(self.resource).encode()
        ]
        protocols = ", ".join(self.protocols)
        key = self._key
        version = '{}'.format(constants.WS_VERSION)
        headers = [
            ('Upgrade', 'websocket'),
            ('Connection', 'Upgrade'),
            ('Sec-WebSocket-Protocol', protocols.encode()),
            ('Sec-WebSocket-Key', self._key.encode()),
            ('Sec-WebSocket-Version', version.encode())
        ]
        for header, value in headers:
            request.append("{}: {}".format(header, value).encode())
        request.append(b'')
        request_bytes = b'\r\n'.join(request)
        return request_bytes

    def _on_headers(self, headers):
        pass

    def _on_message(message):
        try:
            self.on_message(message)
        except Exception as error:
            log.exception("error in on_message")

    def on_headers(self, headers):
        pass

    def on_message(message):
        pass

