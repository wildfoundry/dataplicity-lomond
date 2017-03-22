from __future__ import unicode_literals


class Error(Exception):
    """Base exception."""
    def __init__(self, msg, *args, **kwargs):
        error_msg = msg.format(*args, **kwargs)
        super(Error, self).__init__(error_msg)


class FrameBuildError(Error):
    """Raised when trying to build an invalid websocket frame."""


class HandshakeError(Error):
    """
    Raised when the server doesn't respond correctly to the websocket
    handshake.

    """


class ProtocolError(Error):
    """Raised in response to a protocol violation."""
    # Results in a a graceful disconnect.


class CriticalProtocolError(Error):
    """Critical protocol error."""
    # An egregious error in the protocol resulting in an immediate
    # disconnect.


class PayloadTooLarge(ProtocolError):
    """The payload length field is too large."""
    # With a max payload of 2**63 bytes, we would run out of memory
    # way before we have to raise this.


class TransportFail(Error):
    """The transport (socket) failed when sending."""
    # Likely indicates the socket failed


class WebSocketUnavailable(Error):
    """The websocket may not be used."""


class WebSocketClosed(WebSocketUnavailable):
    """Raised when attempting to send over a closed websocket."""


class WebSocketClosing(WebSocketUnavailable):
    """Raised when attempting to send over a closing websocket."""
