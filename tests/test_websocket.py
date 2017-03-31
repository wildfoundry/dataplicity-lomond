from lomond.websocket import WebSocket
import pytest


@pytest.fixture
def websocket():
    return WebSocket('ws://example.com')


def test_init(websocket):
    assert isinstance(websocket, WebSocket)
    assert isinstance(websocket.state, WebSocket.State)


def test_repr(websocket):
    assert repr(websocket) == "WebSocket('ws://example.com')"


def test_port_has_to_be_numeric():
    with pytest.raises(ValueError) as e:
        WebSocket('ws://example.com:abc')

    assert str(e.value) == 'illegal port value'


def test_is_secure(websocket):
    assert websocket.is_secure is False
    assert WebSocket('wss://example.com').is_secure is True
