from __future__ import unicode_literals

from ._version import __version__

# A constant used in websocket handshake
# Note, this isn't anything that needs to be secured.
# See https://tools.ietf.org/html/rfc6455#page-7
WS_KEY = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

# Standard since 2011
# https://tools.ietf.org/html/rfc6455
WS_VERSION = 13

# Only report major.minor in version
_version_identifier = '.'.join(__version__.split('.')[:2])

# User agent sent with websocket request
# Default will be DataplicityLomond/<major>.<minor
# e.g "DataplicityLomond/0.1"
USER_AGENT = 'DataplicityLomond/{}'.format(_version_identifier)
