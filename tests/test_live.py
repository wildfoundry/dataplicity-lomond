import pytest

from lomond import events, selectors, WebSocket
from lomond.session import WebsocketSession
from socket_fixtures import get_free_port, LocalWebSocketServer, LocalHTTPServer


@pytest.fixture(scope='module')
def local_ws_url():
    port = get_free_port()
    server = LocalWebSocketServer(
        port,
        messages=[('text', u'foo'), ('binary', b'bar')],
        close_after_messages=True
    )
    server.start()
    yield 'ws://127.0.0.1:{}/echo'.format(port)
    server.stop()


@pytest.fixture(scope='module')
def local_idle_ws_url():
    port = get_free_port()
    server = LocalWebSocketServer(port, messages=[], close_after_messages=False)
    server.start()
    yield 'ws://127.0.0.1:{}/echo'.format(port)
    server.stop()


@pytest.fixture(scope='module')
def local_http_url():
    port = get_free_port()
    server = LocalHTTPServer(port)
    server.start()
    yield 'http://127.0.0.1:{}/'.format(port)
    server.stop()


def test_echo(local_ws_url):
    ws = WebSocket(local_ws_url)
    _events = []
    for event in ws.connect(poll=60, ping_rate=0, auto_pong=False):
        _events.append(event)
    assert len(_events) == 8
    assert _events[0].name == 'connecting'
    assert _events[1].name == 'connected'
    assert _events[2].name == 'ready'
    assert _events[3].name == 'poll'
    assert _events[4].name == 'text'
    assert _events[4].text == u'foo'
    assert _events[5].name == 'binary'
    assert _events[5].data == b'bar'
    assert _events[6].name == 'closing'
    assert _events[7].name == 'disconnected'
    assert _events[7].graceful


def test_echo_poll(local_idle_ws_url):
    ws = WebSocket(local_idle_ws_url)
    _events = []
    polls = 0
    for event in ws.connect(poll=1.0, ping_rate=1.0, auto_pong=True):
        _events.append(event)
        if event.name == 'poll':
            polls += 1
            if polls == 1:
                ws.session._on_event(events.Ping(b'foo'))
            elif polls == 2:
                ws.state.closed = True
                ws.session._sock.close()
    assert polls >= 2


def test_not_ws(local_http_url):
    ws = WebSocket(local_http_url.replace('http://', 'ws://'))
    _events = list(ws.connect())
    assert len(_events) == 4
    assert _events[0].name == 'connecting'
    assert _events[1].name == 'connected'
    assert _events[2].name == 'rejected'
    assert _events[3].name == 'disconnected'
    assert _events[3].graceful


class SelectSession(WebsocketSession):
    _selector_cls = selectors.SelectSelector


def test_not_ws_select(local_http_url):
    """Test against a URL that doesn't serve websockets."""
    ws = WebSocket(local_http_url.replace('http://', 'ws://'))
    _events = list(ws.connect(session_class=SelectSession))
    assert len(_events) == 4
    assert _events[0].name == 'connecting'
    assert _events[1].name == 'connected'
    assert _events[2].name == 'rejected'
    assert _events[3].name == 'disconnected'
    assert _events[3].graceful


def test_no_url_wss():
    """Test against a URL that doesn't serve websockets."""
    ws = WebSocket('wss://foo.test')
    events = list(ws.connect())
    assert len(events) == 2
    assert events[0].name == 'connecting'
    assert events[1].name == 'connect_fail'


def test_no_url_ws():
    """Test against a URL that doesn't serve websockets."""
    ws = WebSocket('ws://foo.test')
    events = list(ws.connect())
    assert len(events) == 2
    assert events[0].name == 'connecting'
    assert events[1].name == 'connect_fail'
