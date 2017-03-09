"""

A message class, built from 1 or more websocket frames.

"""

from __future__ import unicode_literals

import struct

from .opcode import Opcode


class Message(object):
    """Base class for a websocket message."""

    __slots__ = ['opcode']
    _unpack16 = struct.Struct('!H').unpack

    def __init__(self, opcode):
        self.opcode = opcode

    def __repr__(self):
        return "<message {}>".format(Opcode.to_str(self.opcode))

    @classmethod
    def build(cls, frames):
        """Build a message from a sequence of frames."""
        opcode = frames[0].opcode
        payload = b''.join(frame.payload for frame in frames)
        if opcode == Opcode.CLOSE:
            code = None
            reason = ''
            if len(payload) >= 2:
                code = cls._unpack16(payload[:2])[0]
                reason = payload[2:].decode(errors='replace')
            return Close(code, reason)
        elif opcode == Opcode.PING:
            return Ping(payload)
        elif opcode == Opcode.PONG:
            return Pong(payload)
        elif opcode == Opcode.BINARY:
            return Binary(payload)
        elif opcode == Opcode.TEXT:
            return Text(payload.decode(errors='replace'))
        else:
            return Message(opcode)

    @property
    def is_text(self):
        """Check if the message is text."""
        return self.opcode == Opcode.TEXT

    @property
    def is_binary(self):
        """Check if the message is binary."""
        return self.opcode == Opcode.BINARY

    @property
    def is_close(self):
        """Check if this is a close message."""
        return self.opcode == Opcode.CLOSE

    @property
    def is_ping(self):
        """Check if this is a ping message."""
        return self.opcode == Opcode.PING

    @property
    def is_pong(self):
        """Check if this is a pong message."""
        return self.opcode == Opcode.PONG


class Binary(Message):
    """Binary application data."""
    __slots__ = ['data']
    def __init__(self, data):
        self.data = data
        super(Binary, self).__init__(Opcode.BINARY)

    def __repr__(self):
        return "Binary({!r})".format(self.data)


class Text(Message):
    """Text application data."""
    __slots__ = ['text']
    def __init__(self, text):
        self.text = text
        super(Text, self).__init__(Opcode.TEXT)

    def __repr__(self):
        return "Text({!r})".format(self.text)


class Close(Message):
    """Connection close control message."""
    __slots__ = ['code', 'reason']
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        super(Close, self).__init__(Opcode.CLOSE)

    def __repr__(self):
        return "Close({}, {!r})".format(self.code, self.reason)


class Ping(Message):
    """Ping message."""
    __slots__ = ['data']
    def __init__(self, data):
        self.data = data
        super(Ping, self).__init__(Opcode.PING)

    def __repr__(self):
        return "Ping({!r})".format(self.data)


class Pong(Binary):
    """Pong message."""
    __slots__ = ['data']
    def __init__(self, data):
        self.data = data
        super(Pong, self).__init__(Opcode.PONG)

    def __repr__(self):
        return "Pong({!r})".format(self.data)


if __name__ == "__main__":
    msg1 = Text("Hello, World")
    print(msg1)
    msg2 = Close(100, 'going away')
    print(msg2)