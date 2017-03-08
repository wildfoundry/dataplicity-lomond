"""
Functions related to masking Websocket frames.
https://tools.ietf.org/html/rfc6455#section-5.3

# TODO: Use wsaccel for masking

"""

import os
from functools import partial
from itertools import izip, cycle

import six


make_masking_key = partial(os.urandom, 4)


if six.PY2:
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
        return bytes(a ^ b for a, b in izip(cycle(masking_key), data))


if __name__ == "__main__":

    plain = b"Hello, World!"
    key = make_masking_key()

    masked = mask(key, plain)
    print(masked)

    plain = mask(key, masked)
    print(plain)
