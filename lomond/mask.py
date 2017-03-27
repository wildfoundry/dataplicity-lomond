"""
Functions related to masking Websocket frames.
https://tools.ietf.org/html/rfc6455#section-5.3

"""

import os
from functools import partial
from itertools import cycle

import six


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
    # This is about 60 (!) times faster than a simple loop
    _XOR_TABLE = [b''.join(chr(a ^ b) for a in range(256)) for b in range(256)]
    def mask(masking_key, data):
        """XOR mask bytes."""
        a, b, c, d = (_XOR_TABLE[n] for n in bytearray(masking_key))
        data_bytes = bytearray(data)
        data_bytes[::4] = data_bytes[::4].translate(a)
        data_bytes[1::4] = data_bytes[1::4].translate(b)
        data_bytes[2::4] = data_bytes[2::4].translate(c)
        data_bytes[3::4] = data_bytes[3::4].translate(d)
        return bytes(data_bytes)

else:
    # Can't deny the Py3 version is nicer
    def mask(masking_key, data):
        """XOR mask bytes."""
        return bytes(a ^ b for a, b in zip(cycle(masking_key), data))
