from itertools import izip, repeat

import six


if six.PY2:
    def mask(masking_key, data):
        return b''.join(
            chr(ord(a) ^ ord(b))
            for a, b in izip(repeat(masking_key), data)
        )
else:
    # Can't deny the Py3 version is nicer
    def mask(masking_key, data):
        return bytes(a ^ b for a, b in izip(repeat(masking_key), data))
