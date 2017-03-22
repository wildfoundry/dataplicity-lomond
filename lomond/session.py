"""
The session manages the mechanics of receiving and sending data over
the websocket.

"""

from __future__ import print_function
from __future__ import unicode_literals

import logging
import select
import socket
import ssl
import threading
import time

import six

from .frame import Frame
from . import errors
from . import events


log = logging.getLogger('lomond')



class WebsocketSession(object):
    """Manages the mechanics of running the websocket."""

    def __init__(self, websocket):
        self.websocket = websocket

        self._address = (websocket.host, websocket.port)
        self._lock = threading.Lock()

        self._sock = None
        self._poll_start = time.time()
        self._last_ping = time.time()

    def __repr__(self):
        return "<ws-session '{}'>".format(self.websocket.url)

    def write(self, data):
        """Send raw data."""
        with self._lock:
            if self._sock is None:
                raise errors.WebSocketUnavailable('not connected')
            if self.websocket.is_closed:
                raise errors.WebSocketClosed('data not sent')
            if self.websocket.is_closing:
                raise errors.WebSocketClosing('data not sent')
            try:
                self._sock.sendall(data)
            except socket.error as error:
                raise errors.TransportFail(
                    'socket fail; {}',
                    error
                )
            except:
                raise errors.TransportFail(
                    'socket error; {}',
                    error
                )

    def send(self, opcode, data):
        """Send a WS Frame."""
        frame = Frame(opcode, payload=data)
        log.debug('CLI -> SRV : %r', frame)
        self.write(frame.to_bytes())

    class _SocketFail(Exception):
        """Used internally to respond to socket fails."""

    @classmethod
    def _socket_fail(cls, msg, *args, **kwargs):
        """Raises a socket fail error to exit select loop."""
        raise cls._SocketFail(msg.format(*args, **kwargs))

    def _select(self, sock, poll):
        """Wait on data or errors."""
        try:
            reads, _, errors = select.select([sock], [], [sock], poll)
        except select.error as error:
            self._socket_fail("select error; {}", error)
        return reads, errors

    def _connect(self):
        """Creat socket and connect."""
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(30)  # TODO: make a parameter for this?
        if self.websocket.is_secure:
            sock = ssl.wrap_socket(sock)
        sock.connect(self._address)
        return sock

    def _close_socket(self):
        """Close the socket safely."""
        # Is a no-op if the socket is already closed.
        try:
            # Get the write lock, so we can be certain data sending
            # in another thread is sent.
            with self._lock:
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
        except socket.error:
            # Socket is already closed.
            # That's fine, just a no-op.
            pass
        except Exception as error:
            # Paranoia
            log.warn('error closing socket (%s)', error)
        finally:
            self._sock = None

    def _send_request(self):
        """Send the request over the wire."""
        request_bytes = self.websocket.get_request()
        self.write(request_bytes)

    def _check_poll(self, poll):
        """Check if it is time for a poll."""
        current_time = time.time()
        if current_time - self._poll_start >= poll:
            self._poll_start = current_time
            return True
        else:
            return False

    def _check_auto_ping(self, ping_rate):
        """Check if a ping is required."""
        if ping_rate:
            current_time = time.time()
            if current_time - self._last_ping >= ping_rate:
                self._last_ping = current_time
                # TODO: Calculate the round trip time
                self.websocket.send_ping()

    def _recv(self, count):
        """Receive and return pending data from the socket."""
        try:
            if self.websocket.is_secure:
                # exhaust ssl buffer
                recv_bytes = []
                while count:
                    data = self._sock.recv(count)
                    recv_bytes.append(data)
                    count = self._sock.pending()
                return b''.join(recv_bytes)
            else:
                # Plain socket recv
                return self._sock.recv(count)
        except socket.error as error:
            self._socket_fail('recv fail; {}', error)

    def _regular(self, poll, ping_rate):
        """Run regularly to do polling / pings."""
        # Check for regularly running actions.
        if self._check_poll(poll):
            yield events.Poll()
        self._check_auto_ping(ping_rate)

    def _feed(self, data, poll, ping_rate):
        """Feed the websocket, yielding events."""
        # Also emits poll events and sends pings
        for event in self.websocket.feed(data):
            yield event
            for regular_event in self._regular(poll, ping_rate):
                yield regular_event

    def run(self, poll=5, ping_rate=30):
        """Run the websocket."""
        websocket = self.websocket
        url = websocket.url
        # Connecting event
        yield events.Connecting(url)

        # Create socket and connect to remote server
        try:
            sock = self._sock = self._connect()
        except socket.error as error:
            yield events.ConnectFail('{}'.format(error))
            return
        except Exception as error:
            log.error('error connecting to %s; %s', url, error)
            yield events.ConnectFail('error; {}'.format(error))
            return

        # We now have a socket.
        # Send the request.
        try:
            self._send_request()
        except errors.TransportFail as error:
            self._close_socket()
            yield events.ConnectFail('request failed; {}'.format(error))
            return
        except Exception as error:
            self._close_socket()
            log.error('error sending request; %s', error)
            yield events.ConnectFail('request error; {}'.format(error))
            return

        # Connected to the server, but not yet upgraded to websockets
        yield events.Connected(url)
        self._poll_start = time.time()

        try:
            while not websocket.is_closed:
                reads, errors = self._select(sock, poll)

                # Check for polls / pings
                for event in self._regular(poll, ping_rate):
                    yield event

                if reads:
                    data = self._recv(4096)
                    if not data:
                        self._socket_fail('connection lost')
                    for event in self._feed(data, poll, ping_rate):
                        yield event
                if errors:
                    self._socket_fail('socket error')
                    break
        except self._SocketFail as error:
            # Session methods will translate socket errors to this
            # exception. The result is we are disconnected.
            self._close_socket()
            yield events.Disconnected('socket fail; {}'.format(error))
        except Exception as error:
            # It pays to be paranoid.
            log.exception('error in websocket loop')
            self._close_socket()
            yield events.Disconnected('error; {}'.format(error))
        else:
            # websocket instance terminate the loop, which means
            # it was a graceful exit.
            self._close_socket()
            yield events.Disconnected(graceful=True)


if __name__ == "__main__":

    # Test with wstest -m echoserver -w ws://127.0.0.1:9001 -d
    # Get wstest app from http://autobahn.ws/testsuite/

    from .websocket import WebSocket

    #ws = WebSocket('wss://echo.websocket.org')
    ws = WebSocket('ws://127.0.0.1:9001/')
    for event in ws.connect(poll=5):
        print(event)
        if isinstance(event, events.Poll):
            ws.send_text('Hello, World')
            ws.send_binary(b'hello world in binary')

