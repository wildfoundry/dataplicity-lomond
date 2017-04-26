from lomond.session import WebsocketSession
from lomond.websocket import WebSocket
from lomond import errors
import pytest
import socket
from mocket import mocketize
from mocket import Mocket, MocketEntry
import select


@pytest.fixture()
def session(monkeypatch):
    monkeypatch.setattr(
        'os.urandom', lambda len: b'\x00' * len)
    # ^^ the above line will be significant in the test where we want
    # to validate the headers being sent to the socket. Namely, the
    # websocket key which is based on os.urandom. Obviously, we can't
    # have an actual random call here because the test wuldn't be
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
        b'Sec-WebSocket-Key: AAAAAAAAAAAAAAAAAAAAAA==\r\n'
        b'Sec-WebSocket-Version: 13\r\n'
        b'User-Agent: DataplicityLomond/0.1\r\n'
        b'\r\n'
    )
