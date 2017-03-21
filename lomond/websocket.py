"""
Abstract websocket functionality.

"""

from __future__ import print_function
from __future__ import unicode_literals

from base64 import b64encode
from hashlib import sha1
import logging
import os

import six
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


log = logging.getLogger('lomond')


class WebSocket(object):
    """IO independent websocket functionality."""

    class State(object):
        def __init__(self):
            self.stream = WebsocketStream()
            self.session = None
            self.key = b64encode(os.urandom(16))
            self.sent_request = False
            self.closing = False
            self.closed = False

    def __init__(self, url, protocols=None, agent=None):
        self.url = url
        self.protocols = protocols or []
        self.agent = agent or constants.USER_AGENT

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
            self.resource = "{}?{}".format(self.resource, _url.query)

        self.state = self.State()

    def __repr__(self):
        return "WebSocket('{}')".format(self.url)

    @property
    def is_secure(self):
        return self.scheme == 'wss'

    @property
    def is_closing(self):
        return self.state.closing

    @property
    def is_closed(self):
        return self.state.closed

    @property
    def stream(self):
        return self.state.stream

    @property
    def session(self):
        return self.state.session

    @property
    def key(self):
        return self.state.key

    def connect(self,
                session_class=WebsocketSession,
                poll=5,
                ping_rate=30):
        """Connect the websocket to a session."""
        self.reset()
        self.state.session = WebsocketSession(self)
        return self.session.run(poll=poll, ping_rate=ping_rate)

    def reset(self):
        """Reset the state."""
        self.state = self.State()

    __iter__ = connect

    def close(self, code=None, reason=None):
        """Close the websocket."""
        if code is None:
            code = Status.NORMAL
        if reason is None:
            reason = b'goodbye'
        self._send_close(code, reason)
        self.state.closing = True

    def _on_close(self, message):
        """Close logic generator."""
        if message.code in Status.invalid_codes:
            raise errors.ProtocolError(
                'reserved close code ({})',
                message.code
            )
        if self.is_closing:
            yield events.Closed(message.code, message.reason)
            self.state.closing = False
            self.state.closed = True
        else:
            self.close(message.code, message.reason)
            self.state.closing = True

    def disconnect(self):
        """Disconnect the websocket."""
        self.state.closing = False
        self.state.closed = True

    def feed(self, data):
        """Feed with data from the socket."""
        if self.is_closed:
            return
        try:
            session = self.session
            for message in self.stream.feed(data):
                if isinstance(message, Response):
                    response = message
                    try:
                        protocol, extensions = self.on_response(response)
                    except errors.HandshakeError as error:
                        self.disconnect()
                        yield events.Rejected(response, str(error))
                        break
                    else:
                        yield events.Ready(response, protocol, extensions)
                else:
                    if message.is_close:
                        for event in self._on_close(message):
                            yield event
                    elif message.is_ping:
                        session.send(Opcode.PONG, message.data)
                    elif message.is_pong:
                        yield events.Pong(message.data)
                    elif message.is_binary:
                        yield events.Binary(message.data)
                    elif message.is_text:
                        yield events.Text(message.text)
                    else:
                        yield events.UnknownMessage(message)
                if self.is_closed:
                    break

        except errors.CriticalProtocolError as error:
            # An error that warrants an immediate disconnect.
            # Usually invalid unicode.
            log.debug('critical protocol error; %s', error)
            self.disconnect()

        except errors.ProtocolError as error:
            # A violation of the protocol that allows for a graceful
            # disconnect.
            log.debug('protocol error; %s', error)
            self.close(Status.PROTOCOL_ERROR, six.text_type(error))
            self.disconnect()

        except GeneratorExit:
            log.warn('disconnecting websocket')
            self.disconnect()

    def get_request(self):
        """Get the request (in bytes)"""
        request = [
            "GET {} HTTP/1.1".format(self.resource).encode('utf-8')
        ]
        protocols = ", ".join(self.protocols)
        version = '{}'.format(constants.WS_VERSION)
        headers = [
            (b'Host', self._host_port.encode('utf-8')),
            (b'Upgrade', b'websocket'),
            (b'Connection', b'Upgrade'),
            (b'Sec-WebSocket-Protocol', protocols.encode('utf-8')),
            (b'Sec-WebSocket-Key', self.key),
            (b'Sec-WebSocket-Version', version.encode('utf-8')),
            (b'User-Agent', self.agent.encode('utf-8')),
        ]
        for header, value in headers:
            request.append(header + b': ' + value)
        request.append(b'\r\n')
        request_bytes = b'\r\n'.join(request)
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
                upgrade_header.decode('utf-8', errors='replace')
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
                "Sec-WebSocket-Accept challenge failed"
            )

        protocol = response.get(b'sec-websocket-protocol')
        extensions = set(response.get_list(b'sec-websocket-extensions'))
        return protocol, extensions

    def send_ping(self, data=b''):
        """Send a ping request."""
        if not isinstance(data, bytes):
            raise TypeError('data argument must be bytes')
        if len(data) > 125:
            raise ValueError('ping data should be <= 125 bytes')
        self.session.send(Opcode.PING, data)

    def send_pong(self, data):
        """Send a ping request."""
        if not isinstance(data, bytes):
            raise TypeError('data argument must be bytes')
        if len(data) > 125:
            raise ValueError('ping data should be <= 125 bytes')
        self.session.send(Opcode.PONG, data)

    def send_binary(self, data):
        """Send a binary frame."""
        if not isinstance(data, bytes):
            raise TypeError('data argument must be bytes')
        self.session.send(Opcode.BINARY, data)

    def send_text(self, text):
        """Send a text frame."""
        if not isinstance(text, six.text_type):
            raise TypeError('text argument must be bytes')
        self.session.send(Opcode.TEXT, text.encode('utf-8', errors='replace'))

    def _send_close(self, code, reason):
        """Send a close frame."""
        frame_bytes = Frame.build_close_payload(code, reason)
        self.session.send(Opcode.CLOSE, frame_bytes)
