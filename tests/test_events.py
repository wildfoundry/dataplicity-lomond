from lomond import events
import pytest
import six


@pytest.mark.parametrize("event_object, expected", [
    (events.Event(), 'Event()'),
    (
        events.Binary(b'\xef' * 17),
        "Binary(%r + 1 bytes)" % six.b('\xef' * 16)
    ),
    (events.Binary(b'\x01'), "Binary(%r)" % six.b('\x01')),
    (events.Text('A' * 17), 'Text(%r + 1 chars)' % ('A' * 16)),
    (events.Text('A'), "Text('A')"),
    (
        events.Connecting('http://example.com'),
        "Connecting(url='http://example.com')"
    ),
    (events.ConnectFail('404'), "ConnectFail('404')"),
    (
        events.Rejected('401', 'Insufficient permissions'),
        "Rejected('401', 'Insufficient permissions')"
    ),
    (
        events.Ready('200', 'HTTP', []),
        "Ready('200', protocol='HTTP', extensions=[])"
    ),
    (events.Disconnected(), "Disconnected('closed', graceful=False)"),
    (events.Disconnected('error'), "Disconnected('error', graceful=False)"),
    (
        events.Disconnected('bye', graceful=True),
        "Disconnected('bye', graceful=True)"
    ),
    (events.Closed(1, 'closed'), "Closed(1, 'closed')"),
    (events.UnknownMessage('?.!'), "UnknownMessage()"),
    (events.Ping('o |'), "Ping('o |')"),
    (events.Pong('  | o'), "Pong('  | o')"),
    (events.BackOff(0.1), "BackOff(delay=0.1)")
])
def test_repr(event_object, expected):
    assert isinstance(event_object, events.Event)
    assert repr(event_object) == expected
