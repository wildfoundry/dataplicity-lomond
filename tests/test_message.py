import lomond.message
from lomond.message import Message
from lomond.opcode import Opcode
from lomond.frame import Frame
from lomond.errors import ProtocolError
import pytest


def test_constructor():
    msg = Message(Opcode.TEXT)
    assert isinstance(msg, Message)
    assert msg.opcode == Opcode.TEXT
    assert repr(msg) == '<message TEXT>'


@pytest.mark.parametrize("opcode, message_class, attrname", [
    (Opcode.CLOSE, lomond.message.Close, 'is_close'),
    (Opcode.PING, lomond.message.Ping, 'is_ping'),
    (Opcode.PONG, lomond.message.Pong, 'is_pong'),
    (Opcode.BINARY, lomond.message.Binary, 'is_binary'),
    (Opcode.TEXT, lomond.message.Text, 'is_text'),
])
def test_build_control_messages(opcode, message_class, attrname):
    frames = [
        Frame(opcode)
    ]

    msg = Message.build(frames)

    assert isinstance(msg, message_class)
    # check if the message passes is_{type} attribute test
    assert getattr(msg, attrname) is True
    # also, check if the message doesn't pass any other is_{type} attribute
    # test
    props = filter(
        lambda prop: prop != attrname and prop.startswith('is_'),
        dir(msg)
    )

    for prop in props:
        assert getattr(msg, prop) is False

    # let's check the repr as well
    if opcode not in (Opcode.TEXT, Opcode.CLOSE):
        assert repr(msg) == "<message %s %s>" % (
            Opcode.to_str(opcode), repr(b'')
        )


def test_build_regular_message():
    msg = Message.build([Frame(Opcode.CONTINUATION)])
    assert isinstance(msg, Message)


def test_repr_for_text():
    msg = Message.build([Frame(Opcode.TEXT)])
    assert repr(msg) == "<message TEXT %s>" % repr(u'')


def test_repr_for_close():
    msg = lomond.message.Close(1, b'1234')
    assert repr(msg) == "<message CLOSE 1, %s>" % repr(b'1234')


def test_close_payload_has_to_be_longer_than_1_byte():
    with pytest.raises(ProtocolError) as e:
        lomond.message.Close.from_payload(b'1')
    assert str(e.value) == "invalid close frame payload"


def test_close_long_payload():
    msg = lomond.message.Close.from_payload(b'\x00\x01\x41')
    assert msg.code == 1
    assert msg.reason == 'A'
