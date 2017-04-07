from lomond.stream import WebsocketStream, FrameParser
from lomond.errors import ProtocolError
import pytest


@pytest.fixture
def stream():
    return WebsocketStream()


def test_constructor(stream):
    assert isinstance(stream, WebsocketStream)


def test_feed(stream):
    data = (
        b'Connection:Keep-Alive\r\nUser-Agent:Test\r\n\r\n'
        b'\x81\x81\x00\x00\x00\x00A'
    )

    feed = list(stream.feed(data))

    assert len(feed) == 2


def test_feed_without_headers_results_in_noop(stream):
    data = b'\x81\x81\x00\x00\x00\x00A'

    assert len(list(stream.feed(data))) == 0


def test_continuation_frames_validation(stream):
    data = (
        b'Connection:Keep-Alive\r\nUser-Agent:Test\r\n\r\n'
        b'\x01\x01A\x81\x01A'
    )

    with pytest.raises(ProtocolError) as e:
        list(stream.feed(data))

    assert str(e.value) == 'continuation frame expected'
