from lomond.websocket import WebSocket
from lomond.stream import WebsocketStream
from lomond.session import WebsocketSession
from lomond.events import Ready, Ping, Pong, Binary, Text
from lomond.message import Close
from lomond.errors import ProtocolError
import pytest
from base64 import b64decode


class FakeSession(object):
    def run(self, *args, **kwargs):
        pass

    def send(self, opcode, bytes):
        pass


@pytest.fixture
def websocket():
    ws = WebSocket('ws://example.com')
    return ws


@pytest.fixture
def websocket_with_fake_session(monkeypatch):
    monkeypatch.setattr(
        'os.urandom', lambda len: b'\x00' * len)

    ws = WebSocket('ws://example.com')
    ws.state.session = FakeSession()
    return ws


def generate_data(*frames):
    payload = [
        b'HTTP/1.1 101 Switching Protocols\r\n',
        b'Upgrade: websocket\r\n',
        b'Connection: Upgrade\r\n',
        b'User-Agent: Test\r\n',
        b'Sec-WebSocket-Key: AAAAAAAAAAAAAAAAAAAAAA==\r\n',
        b'Sec-WebSocket-Accept: icx+yqv66kxgm0fcwalwlflwtai=\r\n',
        b'\r\n'
    ]
    payload.extend(frames)

    return b''.join(payload)


def test_init(websocket):
    assert isinstance(websocket, WebSocket)
    assert isinstance(websocket.state, WebSocket.State)
    assert websocket.resource == '/'
    assert len(b64decode(websocket.key)) == 16
    assert websocket.session is None
    assert isinstance(websocket.stream, WebsocketStream)


def test_init_with_query():
    ws = WebSocket('ws://example.com/resource?query')
    assert ws.resource == '/resource?query'


def test_repr(websocket):
    assert repr(websocket) == "WebSocket('ws://example.com')"


def test_port_has_to_be_numeric():
    with pytest.raises(ValueError) as e:
        WebSocket('ws://example.com:abc')

    assert str(e.value) == 'illegal port value'


def test_is_secure(websocket):
    assert websocket.is_secure is False
    assert WebSocket('wss://example.com').is_secure is True


def test_get_request(monkeypatch):
    monkeypatch.setattr(
        'os.urandom', lambda len: b'\x00' * len)
    ws = websocket()
    assert ws.get_request() == (
        b'GET / HTTP/1.1\r\n'
        b'Host: example.com:80\r\n'
        b'Upgrade: websocket\r\n'
        b'Connection: Upgrade\r\n'
        b'Sec-WebSocket-Protocol: \r\n'
        b'Sec-WebSocket-Key: AAAAAAAAAAAAAAAAAAAAAA==\r\n'
        #                    ^^^^^^^^^^^^^^^^^^^^^^^^
        #                     b64encode('\x00' * 16)
        b'Sec-WebSocket-Version: 13\r\n'
        b'User-Agent: DataplicityLomond/0.1\r\n'
        b'\r\n'
    )


def test_connect(websocket):
    websocket.connect()
    assert isinstance(websocket.session, WebsocketSession)


# def test_calling_close_sets_is_closing_flag(websocket):
#     websocket.close()
#     assert websocket.is_closing is True


def test_feed(websocket):
    data = (
        b'Connection:Keep-Alive\r\nUser-Agent:Test\r\n\r\n'
        b'\x81\x81\x00\x00\x00\x00A'
    )

    list(websocket.feed(data))


def test_close(websocket_with_fake_session):
    ws = websocket_with_fake_session
    assert ws.is_closing is False

    data = generate_data(
        b'\x88\x80\xba51e'
    )

    # we call the list to actually run the generator
    list(ws.feed(data))

    assert ws.is_closing is True


@pytest.mark.parametrize('payload, expected', [
    (b'\x89\x80\xbcB\x9f;', Ping),
    (b'\x8a\x80?\x18\x16\x01', Pong),
    (b'\x82\x81F_u\xdfG', Binary),
    (b'\x81\x83\x99\xdeU\xab\xd8\x9c\x16', Text)
])
def test_regular_message(websocket_with_fake_session, payload, expected):
    ws = websocket_with_fake_session

    data = generate_data(payload)

    events = list(ws.feed(data))

    assert len(events) == 2
    assert isinstance(events[0], Ready)
    assert isinstance(events[1], expected)


def test_close_with_reserved_code(websocket):
    reserved_message = Close(code=1005, reason='reserved-close-code')
    with pytest.raises(ProtocolError):
        next(websocket._on_close(reserved_message))
