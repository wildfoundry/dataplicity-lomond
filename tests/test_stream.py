from lomond.stream import WebsocketStream
from lomond.errors import ProtocolError
from lomond.response import Response
import pytest


@pytest.fixture
def stream():
    return WebsocketStream()


def test_feed(stream):
    data = (
        b'Connection:Keep-Alive\r\nUser-Agent:Test\r\n\r\n'
        b'\x81\x81\x00\x00\x00\x00A'
        # the first \x81 designates a type TEXT and some magic masks set
        # the second \x81 stands for XOR masking being used, and a length of 1
        # the following 4 \x00 are the XOR masking key, and lastly, a letter
        # A is inserted as the actual payload
        #
        # for in-depth explanation what the above bytes mean, please refer to
        # test_frame_parser.py
    )

    feed = list(stream.feed(data))

    assert len(feed) == 2
    # the feed method is expected to produce the http response object and the
    # binary payload. The one used here is very dummy (i.e. it doesn't contain
    # HTTP protocol version, method used, etc), but since we don't actually
    # validate it, this will do.
    assert isinstance(feed[0], Response)
    # decoded payload
    # one could also use isinstance(feed[1], Text) here
    assert feed[1].is_text
    assert feed[1].text == 'A'


def test_feed_without_headers_results_in_noop(stream):
    # please refer to test_feed for meaning of these bytes
    data = b'\x81\x81\x00\x00\x00\x00A'

    # without the header present, the feeder should stop, regardless of the
    # payload
    assert len(list(stream.feed(data))) == 0


def test_continuation_frames_validation(stream):
    data = (
        b'Connection:Keep-Alive\r\nUser-Agent:Test\r\n\r\n'
        b'\x01\x01A\x81\x01A'
        # the most significant bit in first byte of the binary message means
        # that FIN=0 and therefore this is supposed to be a continuation frame
        # however, the second part of bytes (which starts right after the first
        # letter A has a byte combination which state that this is a TEXT
        # message. Thefore the parser cannot continue previous frame and should
        # fail with an explicit message)
        #
        # please refer to test_frame_parser for in-depth explanation of all
        # bits and bytes of the websocket payloads
    )

    with pytest.raises(ProtocolError) as e:
        list(stream.feed(data))

    assert str(e.value) == 'continuation frame expected'
