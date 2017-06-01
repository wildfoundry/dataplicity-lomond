from lomond import events
import pytest
import six


test_cases = [
    (events.Event(), 'Event()'),
    (events.Text('A' * 25), 'Text(%r + 1 chars)' % ('A' * 24)),
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
    (events.Closing(1, 'closing'), "Closing(1, 'closed')"),
    (events.UnknownMessage('?.!'), "UnknownMessage()"),
    (events.Ping('o |'), "Ping('o |')"),
    (events.Pong('  | o'), "Pong('  | o')"),
    (events.BackOff(0.1), "BackOff(delay=0.1)")
]

# we are splitting these two test cases into separate branches, because the
# underlying code which implements __repr__ calls __repr__ of the passed
# object. As we all know, Python2 treats b'' as a simple string, however
# Python3 understands it as a different type (bytes) and represents it with a
# leading b''. This could be done in a portable way using six in one line, but
# the code would be somewhat misleading
if six.PY2:
    test_cases.extend([
        (
            events.Binary(b'\xef' * 25),
            "Binary('%s' + 1 bytes)" % ('\\xef' * 24)
        ),
        (events.Binary(b'\x01'), "Binary('\\x01')"),
    ])
elif six.PY3:
    test_cases.extend([
        (
            events.Binary(b'\xef' * 25),
            "Binary(%s + 1 bytes)" % (b'\xef' * 24)
        ),
        (events.Binary(b'\x01'), "Binary(b'\\x01')"),
    ])


@pytest.mark.parametrize("event_object, expected", test_cases)
def test_repr(event_object, expected):
    assert isinstance(event_object, events.Event)
    assert repr(event_object) == expected
