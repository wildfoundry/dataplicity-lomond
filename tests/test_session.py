from lomond.session import WebsocketSession
from lomond.websocket import WebSocket
from lomond import errors
import pytest
import socket


@pytest.fixture()
def session():
    return WebsocketSession(WebSocket('ws://example.com/'))


class FakeSocket(object):
    pass


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
    assert repr(session) == "<ws-session 'ws://example.com/'>"
