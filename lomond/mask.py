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
    from itertools import izip
    def mask(masking_key, data):
        """XOR mask bytes."""
        return b''.join(
            chr(ord(a) ^ ord(b))
            for a, b in izip(cycle(masking_key), data)
        )
else:
    # Can't deny the Py3 version is nicer
    def mask(masking_key, data):
        """XOR mask bytes."""
        return bytes(a ^ b for a, b in zip(cycle(masking_key), data))


if __name__ == "__main__":

    plain = b"Hello, World!"
    key = make_masking_key()

    masked = mask(key, plain)
    print(masked)

    plain = mask(key, masked)
    print(plain)
