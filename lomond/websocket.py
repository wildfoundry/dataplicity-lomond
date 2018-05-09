"""
Abstract websocket functionality.

"""

from __future__ import print_function
from __future__ import unicode_literals

from base64 import b64encode
from hashlib import sha1
import json
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
    """IO independent websocket functionality.

    :param str url: A websocket URL, must have a ``ws://`` or ``wss://``
        protocol.
    :param dict proxies: A dict containing ``'http'`` or ``'https'``
        urls to a proxy server, or ``None`` to attempt to auto-detect
        proxies from environment. Pass an empty dict to disable proxy.
    :param list protocols: A list of supported protocols (defaults to
        no protocols).
    :param str agent: A user agent string to be sent in the header. The
        default uses the value ``USER_AGENT`` defined in
        :mod:`lomond.constants`.

    """

    class State(object):
        def __init__(self):
            self.stream = WebsocketStream()
            self.session = None
            self.key = b64encode(os.urandom(16))
            self.sent_request = False
            self.closing = False
            self.closed = False
            self.sent_close_time = None

    def __init__(self, url, proxies=None, protocols=None, agent=None):
        self.url = url
        self.proxies = self._detect_proxies() if proxies is None else proxies
        self.protocols = protocols or []
        self.agent = agent or constants.USER_AGENT
        self._headers = []
        _url = urlparse(url)
        self.scheme = _url.scheme
        self.host = _url.hostname
        self.port = (
            int(_url.port)
            if _url.port else
            (443 if self.scheme == 'wss' else 80)
        )
        self._host_port = "{}:{}".format(self.host, self.port)
        self.resource = _url.path or '/'
        if _url.query:
            self.resource = "{}?{}".format(self.resource, _url.query)

        self.state = self.State()

    @classmethod
    def _detect_proxies(cls):
        """Get proxy information form environment."""
        proxies = {
            'http': os.environ.get('HTTP_PROXY'),
            'https': os.environ.get('HTTPS_PROXY')
        }
        return proxies

    def __repr__(self):
        return "WebSocket('{}')".format(self.url)

    @property
    def is_secure(self):
        """Boolean that indicates if the websocket is over ssl (i.e. the
        `wss` protocol).

        """
        return self.scheme == 'wss'

    @property
    def is_closing(self):
        """Boolean that indicates if the websocket is in a closing
        state. No further messages may be sent when a websocket is
        closing.

        """
        return self.state.closing

    @property
    def is_active(self):
        """Boolean that indicates the socket is 'active' i.e. not in
        a closing state.

        """
        return not self.state.closing and not self.state.closed

    @property
    def sent_close_time(self):
        """The time (seconds since session start) when a close packet
        was sent (or None if no close packet has been sent).

        """
        return self.state.sent_close_time

    @property
    def is_closed(self):
        """Flag that indicates if the websocket is closed."""
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the session (and potentially a socket) on exit."""
        if self.session is not None:
            self.session.close()

    def add_header(self, header, value):
        """Add a custom header to the websocket request.

        :param bytes header: Name of the header.
        :param bytes value: Value of the header.

        """
        if not isinstance(header, bytes):
            raise TypeError("'header' must be bytes")
        if not isinstance(value, bytes):
            raise TypeError("'value' must be bytes")
        self._headers.append((header, value))

    def connect(self,
                session_class=WebsocketSession,
                poll=5.0,
                ping_rate=30.0,
                ping_timeout=None,
                auto_pong=True,
                close_timeout=30.0):
        """Connect the websocket to a session.

        :param session_class: An object to manage the *session*. This
            object is an extension mechanism that will allow the
            WebSocket to be *driven* by different back-ends. For now,
            treat it as an implementation detail and leave it as the
            default.
        :param float poll: Rate (in seconds) that poll events should be
            generated.
        :param float ping_rate: Rate that ping packets should be sent.
            Set to `0` to disable auto pings.
        :param float ping_timeout: Maximum time in seconds to wait for a
            pong response before disconnecting. Set to `None` (default)
            to disable. If set, double `ping_rate` would be a good
            starting point.
        :param bool auto_pong: Enable (default) automatic response to
            ping events.
        :param float close_timeout: Seconds to wait for server to
            respond to a close packet, before closing the socket. Set to
            `None` or `0` to disable the timeout.
        :returns: An iterable of :class:`~lomond.event.Event` instances.

        """
        self.reset()
        self.state.session = session = session_class(self)
        run_generator = session.run(
            poll=poll,
            ping_rate=ping_rate,
            ping_timeout=ping_timeout,
            auto_pong=auto_pong,
            close_timeout=close_timeout
        )
        return run_generator

    def reset(self):
        """Reset the state."""
        self.state = self.State()

    __iter__ = connect

    def close(self, code=Status.NORMAL, reason=b'goodbye'):
        """Close the websocket.

        :param int code: A closing code, which should probably be one of
            the enumerations in :class:`lomond.status.Status` or a valid
            value as specified in
            https://tools.ietf.org/html/rfc6455#section-7.4
        :param str reason: A short descriptive reason why the websocket
            is closing. This value is intended for the remote end to
            help in debugging.

        .. note::
            Closing the websocket won't exit the main loop immediately;
            it will put the websocket in to a *closing* state while it
            waits for the server to echo back a close packet. No data
            may be sent by the application when the websocket is
            closing.

        """
        if self.is_closed:
            log.debug('%r already closed', self)
        else:
            if not self.is_closing:
                self._send_close(code, reason)
                self.state.closing = True
                self.state.sent_close_time = self.session.session_time

    def _on_close(self, message):
        """Close logic generator."""
        if message.code in Status.invalid_codes:
            raise errors.ProtocolError(
                'reserved close code ({})',
                message.code
            )
        if self.is_closed:
            return
        if self.is_closing:
            yield events.Closed(message.code, message.reason)
            self.state.closing = False
            self.state.closed = True
        else:
            yield events.Closing(message.code, message.reason)
            self.close(message.code, message.reason)
            self.state.closing = True

    def on_disconnect(self):
        """Called on disconnect."""
        self.state.session.close()
        self.state.closing = False
        self.state.closed = True

    def feed(self, data):
        """Feed with data from the socket, and yield any events.

        This method is called by the Session object, and is not needed
        for normal use.

        :param bytes data: data received over a socket.

        """
        if self.is_closed:
            return
        try:
            for message in self.stream.feed(data):
                if isinstance(message, Response):
                    response = message
                    try:
                        protocol, extensions = self.on_response(response)
                    except errors.HandshakeError as error:
                        self.on_disconnect()
                        yield events.Rejected(response, six.text_type(error))
                        break
                    else:
                        yield events.Ready(response, protocol, extensions)
                else:
                    if message.is_close:
                        for event in self._on_close(message):
                            yield event
                    elif message.is_ping:
                        yield events.Ping(message.data)
                    elif message.is_pong:
                        yield events.Pong(message.data)
                    elif message.is_binary:
                        yield events.Binary(message.data)
                    elif message.is_text:
                        yield events.Text(message.text)
                if self.is_closed:
                    break

        except errors.CriticalProtocolError as error:
            # An error that warrants an immediate disconnect.
            # Usually invalid unicode.
            log.debug('critical protocol error; %s', error)
            self.on_disconnect()

        except errors.ProtocolError as error:
            # A violation of the protocol that allows for a graceful
            # disconnect.
            log.debug('protocol error; %s', error)
            self.close(Status.PROTOCOL_ERROR, six.text_type(error))
            self.on_disconnect()

        except GeneratorExit:
            # The generator has exited prematurely, due to an exception
            # handling the event.
            log.warning('disconnecting websocket')
            self.on_disconnect()

    def build_request(self):
        """Get the websocket request (in bytes).

        This method is called from the session, and should not be
        invoked explicitly.

        """
        request = [
            "GET {} HTTP/1.1".format(self.resource).encode('utf-8')
        ]
        version = '{}'.format(constants.WS_VERSION)
        headers = self._headers[:]

        headers.extend([
            (b'Host', self._host_port.encode('utf-8')),
            (b'Upgrade', b'websocket'),
            (b'Connection', b'Upgrade'),
            (b'Sec-WebSocket-Key', self.key),
            (b'Sec-WebSocket-Version', version.encode('utf-8')),
            (b'User-Agent', self.agent.encode('utf-8')),
        ])
        if self.protocols:
            protocols = ", ".join(self.protocols).encode('utf-8')
            headers.append((b'Sec-WebSocket-Protocol', protocols))
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
        """Send a ping packet.

        :param bytes data: Data to send in the ping message (must be <=
            125 bytes).
        :raises TypeError: If `data` is not bytes.
        :raises ValueError: If `data` is > 125 bytes.

        """
        if not isinstance(data, bytes):
            raise TypeError('data argument must be bytes')
        if len(data) > 125:
            raise ValueError('ping data should be <= 125 bytes')
        self.session.send(Opcode.PING, data)

    def send_pong(self, data):
        """Send a pong packet.

        :param bytes data: Data to send in the ping message (must be <=
            125 bytes).

        A *pong* may be sent in response to a ping, or unsolicited to
        keep the connection alive.

        :raises TypeError: If `data` is not bytes.
        :raises ValueError: If `data` is > 125 bytes.

        """
        if not isinstance(data, bytes):
            raise TypeError('data argument must be bytes')
        if len(data) > 125:
            raise ValueError('pong data should be <= 125 bytes')
        self.session.send(Opcode.PONG, data)

    def send_binary(self, data):
        """Send a binary message.

        :param bytes data: Binary data to send.
        :raises TypeError: If data is not bytes.

        """
        if not isinstance(data, bytes):
            raise TypeError('data argument must be bytes')
        self.session.send(Opcode.BINARY, data)

    def send_json(self, _obj=Ellipsis, **kwargs):
        """Encode an object as JSON and send a text message.

        The object to encode may be specified as a single positional
        argument OR if as keyword arguments which will be encoded as a
        JSON object. The following two lines will send the
        same JSON::

            websocket.send_json({'foo': 'bar'})
            websocket.send_json(foo='bar')

        :param obj: An object to be encoded as JSON.
        :raises TypeError: If `obj` could not be encoded as JSON.

        """
        if kwargs and _obj is not Ellipsis:
            raise ValueError(
                'send_json requires positional argument OR keyword arguments'
            )
        json_obj = json.dumps(_obj if _obj is not Ellipsis else kwargs)
        self.send_text(
            json_obj.decode('utf-8')
            if six.PY2
            else json_obj
        )

    def send_text(self, text):
        """Send a text message.

        :param str text: Text to send.
        :raises TypeError: If data is not str (or unicode on Py2).

        """
        if not isinstance(text, six.text_type):
            raise TypeError('text argument must not be bytes')
        self.session.send(Opcode.TEXT, text.encode('utf-8'))

    def _send_close(self, code, reason):
        """Send a close frame."""
        frame_bytes = Frame.build_close_payload(code, reason)
        try:
            self.session.send(Opcode.CLOSE, frame_bytes)
        except (errors.WebSocketUnavailable, errors.TransportFail):
            return False
        else:
            return True
