import calendar
import select
import socket
from datetime import datetime
import sys

import pytest
from freezegun import freeze_time
from lomond import errors, events
from lomond import constants
from lomond.session import WebsocketSession
from lomond.websocket import WebSocket
from mocket import Mocket, MocketEntry, mocketize


@pytest.fixture()
def session(monkeypatch):
    monkeypatch.setattr(
        'os.urandom', b'\xaa'.__mul__
    )
    # ^^ the above line will be significant in the test where we want
    # to validate the headers being sent to the socket. Namely, the
    # websocket key which is based on os.urandom. Obviously, we can't
    # have an actual random call here because the test wouldn't be
    # deterministic, hence this sequence of bytes.

    return WebsocketSession(WebSocket('wss://example.com/'))


@pytest.fixture()
# @mocketize
def session_with_socket(monkeypatch):
    Mocket.register(
        MocketEntry(
            ('example.com', 80),
            [b'some binary data']
        )
    )

    session_obj = session(monkeypatch)
    return session_obj


class FakeSocket(object):
    def __init__(self, *args, **kwargs):
        self.buffer = b''
        self._sendall = kwargs.get('sendall', None)

    def fileno(self):
        return 999

    def recv(self, *args, **kwargs):
        raise ValueError('this is a test')

    def shutdown(self, *args, **kwargs):
        pass

    def close(self):
        raise socket.error('already closed')

    def sendall(self, data):
        self.buffer += data
        if callable(self._sendall):
            self._sendall(data)

    def pending(self):
        return 0


def test_write_without_sock_fails(session):
    with pytest.raises(errors.WebSocketUnavailable) as e:
        session.write(b'\x01')

    assert str(e.value) == 'not connected'


def test_write_with_closed_websocket_fails(session):
    session.websocket.state.closed = True
    session._sock = FakeSocket()
    with pytest.raises(errors.WebSocketClosed) as e:
        session.write(b'\x01')
    assert str(e.value) == 'data not sent'


def test_write_with_closing_websocket_fails(session):
    session.websocket.state.closing = True
    session._sock = FakeSocket()
    with pytest.raises(errors.WebSocketClosing) as e:
        session.write(b'\x01')
    assert str(e.value) == 'data not sent'


def test_socket_error_propagates(session):
    def sendall(data):
        raise socket.error('just testing errors')

    session._sock = FakeSocket()
    session._sock.sendall = sendall
    with pytest.raises(errors.TransportFail) as e:
        session.write(b'\x01')

    assert str(e.value) == 'socket fail; just testing errors'


def test_non_network_error_propagates(session):
    def sendall(data):
        raise ValueError('some random exception')

    session._sock = FakeSocket()
    session._sock.sendall = sendall

    with pytest.raises(errors.TransportFail) as e:
        session.write(b'\x01')

    assert str(e.value) == 'socket error; some random exception'


def test_repr(session):
    assert repr(session) == "<ws-session 'wss://example.com/'>"


def test_close_socket(session, mocker):
    session._sock = FakeSocket()

    mocker.spy(FakeSocket, 'shutdown')
    mocker.spy(FakeSocket, 'close')

    session._close_socket()

    assert FakeSocket.shutdown.call_count == 1
    assert FakeSocket.close.call_count == 1


@mocketize
def test_connect(session, mocker):
    Mocket.register(
        MocketEntry(
            ('example.com', 80),
            [b'some binary data']
        )
    )
    _socket = session._connect()
    assert isinstance(_socket, socket.socket)


@mocketize
def test_socket_fail(session, mocker):
    def select_that_throws_exception(*args, **kwargs):
        raise select.error('this is just a test')

    Mocket.register(
        MocketEntry(
            ('example.com', 80),
            [b'some binary data']
        )
    )

    mocker.patch('lomond.session.select.select', select_that_throws_exception)
    with pytest.raises(WebsocketSession._SocketFail):
        session._select(session._sock, poll=5)


def test_send_request(session):
    session._sock = FakeSocket()
    session._send_request()
    assert session._sock.buffer == (
        b'GET / HTTP/1.1\r\n'
        b'Host: example.com:443\r\n'
        b'Upgrade: websocket\r\n'
        b'Connection: Upgrade\r\n'
        b'Sec-WebSocket-Key: qqqqqqqqqqqqqqqqqqqqqg==\r\n'
        b'Sec-WebSocket-Version: 13\r\n'
        b'User-Agent: ' + constants.USER_AGENT.encode('utf-8') + b'\r\n'
        b'\r\n'
    )


def test_run_with_socket_open_error(session):
    def connect_which_raises_error():
        raise socket.error('socket.error during connect')

    session._connect = connect_which_raises_error

    _events = list(session.run())

    assert len(_events) == 2

    assert isinstance(_events[0], events.Connecting)
    assert _events[0].url == 'wss://example.com/'

    assert isinstance(_events[1], events.ConnectFail)
    assert str(_events[1]) == "ConnectFail('socket.error during connect')"


def test_run_with_regular_exception_on_connect(session):
    def connect_which_raises_value_error():
        raise ValueError('socket.error during connect')

    session._connect = connect_which_raises_value_error

    _events = list(session.run())

    assert len(_events) == 2

    assert isinstance(_events[0], events.Connecting)
    assert _events[0].url == 'wss://example.com/'

    assert isinstance(_events[1], events.ConnectFail)
    assert str(_events[1]) == (
        "ConnectFail('error; socket.error during connect')"
    )


def test_run_with_send_request_raising_transport_error(session):
    # _send_request can raise TransportFail inside write() call
    # in order to do that, the socket has to be opened and raise
    # either socket.error or Exception during sendall() call.
    # let's do just that. First of all, the method in question:
    def sendall_which_raises_error(data):
        raise socket.error('error during sendall')

    # here's where the plot thickens. socket connection is established
    # during self._connect, so we have to substitude this method so that
    # it returns our FakeSocket object.

    def return_fake_socket():
        return FakeSocket(sendall=sendall_which_raises_error)

    session._connect = return_fake_socket

    _events = list(session.run())

    assert isinstance(_events[-1], events.ConnectFail)
    assert str(_events[-1]) == (
        "ConnectFail('request failed; socket fail; error during sendall')"
    )


def test_run_with_send_request_raising_exception(session, mocker):
    # exactly like the one above, but a different type of error is raised.
    # this time, we have to set the state of socket to closed, thus forcing
    # lomond to throw a non-socket error;
    def return_fake_socket(self):
        self.websocket.state.closed = True
        return FakeSocket()

    mocker.patch(
        'lomond.session.WebsocketSession._connect', return_fake_socket)

    _events = list(session.run())

    assert isinstance(_events[-1], events.ConnectFail)
    assert str(_events[-1]) == (
        "ConnectFail('request error; data not sent')"
    )


def test_that_on_ping_responds_with_pong(session, mocker):
    # we don't actually care that much for the whole stack underneath,
    # we only want to check whether a certain method was called..
    send_pong = mocker.patch(
        'lomond.websocket.WebSocket.send_pong'
    )

    session._on_ping(events.Ping(b'\x00'))

    assert send_pong.called_with(b'\x00')


def test_error_on_close_socket(caplog, session):
    def close_which_raises_error():
        raise ValueError('a problem occurred')

    session._sock = FakeSocket()
    session._sock.close = close_which_raises_error

    session._close_socket()

    import logging

    assert caplog.record_tuples[-1] == (
        'lomond',
        logging.WARNING,
        'error closing socket (a problem occurred)'
    )


@freeze_time("1994-05-01 18:40:00")
def test_check_poll(session):
    session._poll_start = calendar.timegm(
        datetime(1994, 5, 1, 18, 00, 00).timetuple()
    )
    assert session._check_poll(5 * 60)
    assert not session._check_poll(60 * 60)


@freeze_time("1994-05-01 18:40:00")
def test_check_auto_ping(session, mocker):
    session._last_ping = calendar.timegm(
        datetime(1994, 5, 1, 18, 00, 00).timetuple()
    )

    mocker.patch.object(session.websocket, 'send_ping')

    assert session.websocket.send_ping.call_count == 0

    session._check_auto_ping(15 * 60)

    assert session.websocket.send_ping.call_count == 1
    session._check_auto_ping(36 * 60)
    assert session.websocket.send_ping.call_count == 1


@mocketize
def test_simple_run(monkeypatch, mocker):
    monkeypatch.setattr(
        'os.urandom', b'\x00'.__mul__
    )
    Mocket.register(
        MocketEntry(
            ('example.com', 80),
            [(
                b'HTTP/1.1 101 Switching Protocols\r\n'
                b'Upgrade: websocket\r\n'
                b'Connection: Upgrade\r\n'
                b'Sec-WebSocket-Accept: icx+yqv66kxgm0fcwalwlflwtai=\r\n'
                b'\r\n'
                b'\x81\x81\x00\x00\x00\x00A'
            )]
        )
    )

    # mocket doesn't support .pending() call which is used when ssl is used
    session = WebsocketSession(WebSocket('ws://example.com/'))
    session._last_ping = calendar.timegm(
        datetime(1994, 5, 1, 18, 00, 00).timetuple()
    )
    # well, we have to cheat a little. The thing is, inner loop of
    # run() sets last poll time to time.time and so we would have to
    # wait for some time to actually hit poll / ping. This is not desirable
    # so we can do the following:
    # save original _regular call into _regular_orig
    # (_regular is a first - well, technically, a second) call inside run
    # after _poll_start is set which makes it a nice candidate for monkey-patch
    # location. Here's how we do it:
    session._regular_orig = session._regular

    def _regular_with_fake_poll_start(self, poll, ping_rate, close_timeout):
        # trivial substitute:
        self._poll_start = self._last_ping
        # print(self._regular_orig)
        return self._regular_orig(poll, ping_rate, close_timeout)

    mocker.patch(
        'lomond.session.WebsocketSession._regular',
        _regular_with_fake_poll_start
    )
    mocker.patch(
        'lomond.websocket.WebSocket._send_close')
    mocker.patch.object(session.websocket, 'send_ping')
    mocker.patch(
        'lomond.session.WebsocketSession._select',
        lambda self, sock, poll:[True, False]
    )

    _events = list(session.run())

    assert len(_events) == 6
    assert isinstance(_events[0], events.Connecting)
    assert isinstance(_events[1], events.Connected)
    assert isinstance(_events[2], events.Poll)
    assert isinstance(_events[3], events.Ready)
    assert isinstance(_events[4], events.Text)
    assert isinstance(_events[5], events.Disconnected)


def test_recv_with_secure_websocket(session):
    def fake_recv(self):
        return b'\x01'

    session._sock = FakeSocket()
    session._sock.recv = fake_recv

    assert session._recv(1) == b'\x01'
