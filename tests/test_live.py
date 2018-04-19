import lomond
from lomond import events


def test_echo():
    """Test against public echo server."""
    # TODO: host our own echo server
    ws = lomond.WebSocket('wss://echo.websocket.org')
    events = []
    polls = 0
    for event in ws.connect(poll=60, ping_rate=0, auto_pong=False):
        events.append(event)
        if event.name == 'ready':
            ws.send_text(u'foo')
            ws.send_binary(b'bar')
            polls += 1
            ws.close()

    assert events[0].name == 'connecting'
    assert events[1].name == 'connected'
    assert events[2].name == 'ready'
    assert events[3].name == 'poll'
    assert events[4].name == 'text'
    assert events[4].text == u'foo'
    assert events[5].name == 'binary'
    assert events[5].data == b'bar'
    assert events[6].name == 'closed'
    assert events[7].name == 'disconnected'
    assert events[7].graceful


def test_not_ws():
    """Test against a URL that doesn't serve websockets."""
    ws = lomond.WebSocket('wss://www.willmcgugan.com')
    events = list(ws.connect())
    assert events[0].name == 'connecting'
    assert events[1].name == 'connected'
    assert events[2].name == 'rejected'
    assert events[3].name == 'disconnected'
