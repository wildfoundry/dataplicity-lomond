from __future__ import unicode_literals

import time


class Event(object):
    """Base class for a websocket 'event'."""
    def __init__(self):
        self.received_time = time.time()

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)


class Poll(Event):
    """A generated poll event."""


class Connecting(Event):
    """Connection process has started."""

    def __init__(self, url):
        self.url = url
        super(Connecting, self).__init__()

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.url)


class Connected(Connecting):
    """Connected to server (but not yet received response)."""


class ConnectFail(Event):
    """Connection failed (connectivity related)."""
    def __init__(self, reason):
        self.reason = reason
        super(ConnectFail, self).__init__()

    def __repr__(self):
        return '{}({!r})'.format(
            self.__class__.__name__,
            self.reason,
        )


class Accepted(Event):
    """Server accepted WS connection."""
    def __init__(self, protocol, extensions):
        self.protocol = protocol
        self.extensions = extensions
        super(Accepted, self).__init__()

    def __repr__(self):
        return '{}(protocol={!r}, extensions={!r})'.format(
            self.__class__.__name__,
            self.protocol,
            self.extensions
        )


def Rejected(Event):
    """Server rejected WS connection."""
    def __init__(self, reason):
        self.reason = reason
        super(Rejected, self).__init__()

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.reason)


class Disconnected(Event):
    """Server disconnected."""


class Closed(Event):
    """Websocket connection is closed."""
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        super(Closed, self).__init__()

    def __repr__(self):
        return '{}({!r}, {!r})'.format(
            self.__class__.__name__,
            self.code,
            self.reason,
        )

class UnknownMessage(Event):
    """
    An application message was received, with an unknown
    opcode.
    """
    def __init__(self, message):
        self.message = message
        super(UnknownMessage, self).__init__()


class Binary(Event):
    """An application message was received."""
    def __init__(self, message):
        self.data = message.data
        super(Binary, self).__init__()

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.data)


class Pong(Event):
    """An application message was received."""
    def __init__(self, message):
        self.data = message.data
        super(Pong, self).__init__()

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.data)


class Text(Event):
    """An application text message was received."""
    def __init__(self, message):
        self.text = message.text
        super(Text, self).__init__()

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.text)

