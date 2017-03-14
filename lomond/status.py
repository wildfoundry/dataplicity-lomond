"""
Websocket status codes

https://tools.ietf.org/html/rfc6455#section-7.4

"""

class Status(object):
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002

    BAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_LARGE = 1009
    EXTENSION_FAILED = 1010

    UNEXPECTED_CONDITION = 1011
