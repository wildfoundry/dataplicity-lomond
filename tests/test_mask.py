import lomond.mask
import os
import six


def fake_masking_key():
    return b'\xaa\xff\x7f\xf7'


def test_make_masking_key():
    # well, there isn't much that we can do here - it's random after all
    key = lomond.mask.make_masking_key()
    assert len(key) == 4
    assert type(key) is bytes


def test_masking():
    key = fake_masking_key()
    plain = b"Hello, World"
    masked = lomond.mask.mask(key, plain)
    # Masked byte should look like gibberish
    assert masked == b'\xe2\x9a\x13\x9b\xc5\xd3_\xa0\xc5\x8d\x13\x93'
    # Apply mask again to unmask
    unmasked = lomond.mask.mask(key, masked)
    # Result should be plain text
    assert plain == unmasked
