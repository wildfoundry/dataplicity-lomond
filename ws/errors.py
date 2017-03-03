
class FrameBuildError(Exception):
    pass


class WebsocketError(Exception):
    pass


class ProtocolError(WebsocketError):
    pass


class HandshakeError(Exception):
    pass