from __future__ import unicode_literals

from ._version import __version__

# A constant used in websocket handshake
# Note, this isn't anything that needs to be secured.
# See https://tools.ietf.org/html/rfc6455#page-7
WS_KEY = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
# Standard since 2011
# https://tools.ietf.org/html/rfc6455
WS_VERSION = 13

USER_AGENT = "DataplicityLomond/{}".format(__version__)