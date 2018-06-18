from __future__ import unicode_literals

import zlib


class ParameterError(Exception):
    pass


class Deflate(object):
    """Compress with the Deflate algorith."""

    def __init__(self, decompress_wbits, compress_wbits, no_context_takeover):
        self.decompress_wbits = decompress_wbits
        self.compress_wbits = compress_wbits
        self.no_context_takeover = no_context_takeover
        self._compressobj = zlib.compressobj(
            4, zlib.DEFLATED, -self.compress_wbits
        )
        self.reset_decompressor()

    def reset_decompressor(self):
        """Reset the compressor."""
        self._decompressobj = zlib.decompressobj(-self.decompress_wbits)

    @classmethod
    def from_options(cls, options):
        """Build object from options dict."""
        decompress_wbits = cls.get_wbits(
            options, b"server_max_window_bits", 8, 15
        )
        compress_wbits = cls.get_wbits(
            options, b"client_max_window_bits", 9, 15
        )
        auto_reset = b"server_no_context_takeover" in options
        deflate = Deflate(decompress_wbits, compress_wbits, auto_reset)
        return deflate

    @classmethod
    def get_wbits(cls, options, key, _min, _max):
        _wbits = options.get(key, "15")
        try:
            wbits = int(_wbits)
        except ValueError:
            raise ParameterError("{} is not an integer".format(key))
        if wbits < _min or wbits > _max:
            raise ParameterError("%s=%s is invalid".format(key, wbits))
        return wbits

    def __repr__(self):
        return "Deflate({!r}, {!r}, {!r})".format(
            self.decompress_wbits, self.compress_wbits, self.auto_reset
        )

    def decompress(self, payload):
        """Decompress payload, returned decompressed data."""
        data = (
            self._decompressobj.decompress(payload + b"\x00\x00\xff\xff")
            + self._decompressobj.flush()
        )
        if self.no_context_takeover:
            self.reset_decompressor()
        return data

    def compress(self, payload):
        """Compress payload, return compressed data."""
        data = (
            self._compressobj.compress(payload)
            + self._compressobj.flush(zlib.Z_SYNC_FLUSH)
        )[:-4]
        return data
