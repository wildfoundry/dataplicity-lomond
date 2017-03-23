"""
Events emitted from Lomond Websockets.

Events may be distinguished either by their type or by the `name`
attribute. For example:

    if isinstance(event, events.PING)

or

    if event.name == 'ping'


All events have a `received_time` attribute which is the epoch time
the event was created from the network stream.

"""

from __future__ import unicode_literals

import time


class Event(object):
    """Base class for a websocket 'event'."""
    __slots__ = ['received_time']

    def __init__(self):
        self.received_time = time.time()

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)

    @classmethod
    def _summarize_bytes(cls, data, max_len=16):
        """Avoid spamming logs by truncating byte strings in repr."""
        if len(data) > max_len:
            return "{!r} + {} bytes".format(
                data[:max_len],
                len(data) - max_len
            )
        return repr(data)

    @classmethod
    def _summarize_text(cls, text, max_len=16):
        """Avoid spamming logs by truncating text."""
        if len(text) > max_len:
            return "{!r} + {} chars".format(
                text[:max_len],
                len(text) - max_len
            )
        return repr(text)


class Poll(Event):
    """A generated poll event."""
    name = 'poll'


class Connecting(Event):
    """Connection process has started."""
    __slots__ = ['url']
    name = 'connecting'

    def __init__(self, url):
        self.url = url
        super(Connecting, self).__init__()

    def __repr__(self):
        return "{}(url='{}')".format(self.__class__.__name__, self.url)


class ConnectFail(Event):
    """Connection failed (connectivity related)."""
    __slots__ = ['reason']
    name = 'connect_fail'

    def __init__(self, reason):
        self.reason = reason
        super(ConnectFail, self).__init__()

    def __repr__(self):
        return "{}('{}')".format(
            self.__class__.__name__,
            self.reason,
        )


class Connected(Connecting):
    """Connected to the server (but not yet negotiated websockets)."""
    name = 'connected'


class Rejected(Event):
    """Server rejected WS connection."""
    __slots__ = ['response', 'reason']
    name = 'rejected'

    def __init__(self, response, reason):
        self.response = response
        self.reason = reason
        super(Rejected, self).__init__()

    def __repr__(self):
        return "{}({!r}, '{}')".format(
            self.__class__.__name__,
            self.response,
            self.reason
        )


class Ready(Event):
    """Server accepted WS connection."""
    __slots__ = ['response', 'protocol', 'extensions']
    name = 'ready'

    def __init__(self, response, protocol, extensions):
        self.response = response
        self.protocol = protocol
        self.extensions = extensions
        super(Ready, self).__init__()

    def __repr__(self):
        return '{}({!r}, protocol={!r}, extensions={!r})'.format(
            self.__class__.__name__,
            self.response,
            self.protocol,
            self.extensions
        )


class Disconnected(Event):
    """Server disconnected."""
    __slots__ = ['graceful', 'reason']
    name = 'disconnected'

    def __init__(self, reason='closed', graceful=False):
        self.reason = reason
        self.graceful = graceful
        super(Disconnected, self).__init__()

    def __repr__(self):
        return "{}('{}', graceful={!r})".format(
            self.__class__.__name__,
            self.reason,
            self.graceful
        )


class Closed(Event):
    """Websocket connection is closed."""
    __slots__ = ['code', 'reason']
    name = 'closed'

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
    __slots__ = ['message']
    name = 'unknown'

    def __init__(self, message):
        self.message = message
        super(UnknownMessage, self).__init__()


class Ping(Event):
    """A ping message was received."""
    __slots__ = ['data']
    name = 'ping'

    def __init__(self, data):
        self.data = data
        super(Ping, self).__init__()

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.data)


class Pong(Event):
    """A pong message was received."""
    __slots__ = ['data']
    name = 'pong'

    def __init__(self, data):
        self.data = data
        super(Pong, self).__init__()

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.data)


class Text(Event):
    """An application text message was received."""
    __slots__ = ['text']
    name = 'text'

    def __init__(self, text):
        self.text = text
        super(Text, self).__init__()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self._summarize_text(self.text)
        )


class Binary(Event):
    """An binary application message was received."""
    __slots__ = ['data']
    name = 'binary'

    def __init__(self, data):
        self.data = data
        super(Binary, self).__init__()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self._summarize_bytes(self.data)
        )


class BackOff(Event):
    """Unable to connect, so the client will wait and try again."""
    __slots__ = ['delay']
    name = 'back_off'

    def __init__(self, delay):
        self.delay = delay
        super(BackOff, self).__init__()

    def __repr__(self):
        return "{}(delay={:0.1f})".format(
            self.__class__.__name__,
            self.delay
        )
