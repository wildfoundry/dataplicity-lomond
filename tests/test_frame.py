from lomond.frame import Frame
from lomond.opcode import Opcode
import pytest


@pytest.fixture
def frame_factory():
    def inner(opcode=Opcode.TEXT, payload=b'', fin=1):
        return Frame(opcode, payload, fin=fin)

    return inner


def test_frame_constructor(frame_factory):
    assert isinstance(frame_factory(), object)


def test_length_of_frame(frame_factory):
    frame = frame_factory(Opcode.TEXT, b'\x00' * 137)
    assert len(frame) == 137


def test_repr_of_frame(frame_factory):
    assert repr(frame_factory()) == '<frame TEXT (0 bytes) fin=1>'
    assert repr(
        frame_factory(fin=0)
    ) == '<frame-fragment TEXT (0 bytes) fin=0>'


@pytest.mark.parametrize("opcode, property_name", [
    (Opcode.TEXT, "is_text"),
    (Opcode.BINARY, "is_binary"),
    (Opcode.PING, "is_ping"),
    (Opcode.PONG, "is_pong"),
    (Opcode.CLOSE, "is_close"),
])
def test_attributes(frame_factory, opcode, property_name):
    frame = frame_factory(opcode=opcode)
    # this assertion checks if Frame.property_name is True
    # property_name and opcode are substituded from the tuple above, because
    # pytest calls this function in a loop. So on first pass,
    # opcode=Opcode.Text, property_name=is_text and so on
    assert getattr(frame, property_name) is True
    # this in itself is not enough. We also have to check whether the other
    # properties are False
    # In order to do this, let's collect all the other property names:
    props = filter(
        # we exclude is_control from the list, because
        # frame(Opcode.{PING,PONG,CLOSE}) *are* control frames
        # please note that we also exclude `property_name` from all properties
        # because we test for `property_name` above and obviously the property
        # value can't be True and False at the same time
        lambda prop: prop not in (property_name, 'is_control') and prop.startswith('is_'),  # noqa
        dir(frame)
    )

    for prop in props:
        assert getattr(frame, prop) is False
