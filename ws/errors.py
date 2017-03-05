class Error(Exception):
    def __init__(self, msg, **info):
        error_msg = msg.format(**info)
        super(Error, self).__init__(error_msg)

class FrameBuildError(Error):
    pass


class HandshakeError(Error):
    pass


class WebsocketError(Error):
    pass


class ProtocolError(Error):
    pass


class PayloadTooLarge(Error):
    pass


