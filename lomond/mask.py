"""
Functions related to masking Websocket frames.
https://tools.ietf.org/html/rfc6455#section-5.3

"""

import os
from functools import partial

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

else:
    # This is about 60 (!) times faster than a simple loop
    # -------------------------------------------------------------------------
    # here's a brief explanation of how this works.
    # we're creating an array of 256 translation tables. This will become of
    # significance couple of lines later. In detail, this looks like this:
    # [
    #   ''.join([ 0x00 ^ 0x00, 0x00 ^ 0x01, 0x00 ^ 0x02, ...],
    #   ''.join([ 0x01 ^ 0x00, 0x01 ^ 0x01, 0x01 ^ 0x02, ...],
    #   ''.join([ 0x02 ^ 0x00, 0x02 ^ 0x01, 0x02 ^ 0x02, ...]
    #   ...
    #   ''.join([ 0xff ^ 0x00, 0xff ^ 0x01, 0xff ^ 0x02, ...]
    # ]
    # there are a total of 256 rows in this table, because there are a total of
    # 256 possible bytes.
    if six.PY2:
        _XOR_TABLE = [b''.join(chr(a ^ b) for a in range(256)) for b in range(256)]
    else:
        _XOR_TABLE = [bytes(a ^ b for a in range(256)) for b in range(256)]

    def mask(masking_key, data):
        """XOR mask bytes."""
        a, b, c, d = (_XOR_TABLE[n] for n in bytearray(masking_key))
        # there are 4 bytes in our masking key, that's why we are picking 4
        # variables from the table. Now, here comes the fun part. We are
        # converting `masking_key` to bytearray, which, when iterated over,
        # will covert a byte to the corresponding uint8_t, so if, for instance
        # the `masking_key` will be given as:
        # 'x07\x03\x01\x00'
        # then, n will have the value of 7, 3, 1, 0 with each pass of the
        # for-loop.
        # why is this so significant? Because, as you remember from above,
        # _XOR_TABLE has 256 rows, and the first byte in the xor operation
        # was changing from 0 to 256. Therefore, key from masking_key converted
        # to uint8_t can point us to a translation table for n-th byte from
        # `masking_key`.
        data_bytes = bytearray(data)
        data_bytes[::4] = data_bytes[::4].translate(a)
        data_bytes[1::4] = data_bytes[1::4].translate(b)
        data_bytes[2::4] = data_bytes[2::4].translate(c)
        data_bytes[3::4] = data_bytes[3::4].translate(d)
        # great. The rest is quite easy. array.translate expects a bytearray of
        # length=256. How convenient! It's exactly what we have. The way it
        # works is that it takes an input byte and looks for a byte in the
        # replacement table. So in our case, the replacement table will contain
        # XOR'ed value of this byte by the masking key. Now you may wonder -
        # why are there 4 iterations of this? Well, because there are 4
        # different translation tables for 4 bytes of our masking key - if we
        # wouldn't do this, then we would mess up our input data. So, for the
        # first byte of masking key, we do the following (O = leave original
        # byte, R = replace byte):
        # 0 1 2 3 4 5 6 7 8    ( byte no. )
        # R O O O R O O O R
        # then, for the second byte of the mask, we do:
        # 0 1 2 3 4 5 6 7 8    ( byte no. )
        # O R O O O R O O O
        # please note, that even though byte 0 is marked as 'O', it has already
        # been replaced in the previous step
        return bytes(data_bytes)
        # and voila!
