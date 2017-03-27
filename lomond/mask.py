"""
Functions related to masking Websocket frames.
https://tools.ietf.org/html/rfc6455#section-5.3

"""

import os
from functools import partial
from itertools import cycle

import six


if six.PY2:
    from itertools import izip


try:
    from wsaccel.xormask import XorMaskerSimple
except ImportError:
    XorMaskerSimple = None


make_masking_key = partial(os.urandom, 4)

if XorMaskerSimple is not None:
    # Fast C version (works with Py2 and Py3)
    def mask(masking_key, data):
        return XorMaskerSimple(masking_key).process(data)

elif six.PY2:
    # Python 2 compatible version
    def mask(masking_key, data, _chr=[chr(n) for n in range(256)]):
        """XOR mask bytes."""
        return b''.join(
            _chr[a ^ b]
            for a, b in izip(cycle(bytearray(masking_key)), bytearray(data))
        )
else:
    # Can't deny the Py3 version is nicer
    def mask(masking_key, data):
        """XOR mask bytes."""
        return bytes(a ^ b for a, b in zip(cycle(masking_key), data))
