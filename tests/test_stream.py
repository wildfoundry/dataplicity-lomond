from lomond.stream import WebsocketStream
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
