from __future__ import unicode_literals


class Error(Exception):
    def __init__(self, msg, *args, **kwargs):
        error_msg = msg.format(*args, **kwargs)
        super(Error, self).__init__(error_msg)


class FrameBuildError(Error):
    pass


class HandshakeError(Error):
    pass


class WebsocketError(Error):
    pass


class ProtocolError(Error):
    pass


class PayloadTooLarge(ProtocolError):
    pass


class WebSocketInUse(Error):
    pass


class TransportFail(Error):
    pass


class WebSocketClosed(Error):
    pass
