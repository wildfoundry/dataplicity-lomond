
class FrameBuildError(Exception):
    pass


class HandshakeError(Exception):
    pass


class WebsocketError(Exception):
    pass


class ProtocolError(WebsocketError):
    pass


class PayloadTooLarge(ProtocolError):
    pass


