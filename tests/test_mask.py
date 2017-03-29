import lomond.mask
import os
import six


def fake_masking_key():
    return b'\x00\x00\x00\x00'


def test_make_masking_key():
    # well, there isn't much that we can do here - it's random after all
    key = lomond.mask.make_masking_key()

    assert len(key) == 4
    assert type(key) is bytes


def test_masking_with_empty_mask_doesnt_modify_input(monkeypatch):
    monkeypatch.setattr('lomond.mask.make_masking_key', fake_masking_key)

    my_input = os.urandom(128)
    masked = lomond.mask.mask(lomond.mask.make_masking_key(), my_input)
    # because we're faking the mask to be '\x00', the end result will be our
    # input
    assert masked == my_input
    # let's also make sure that it is bytes rather than regular string
    assert type(masked) == bytes


def test_masking():
    my_input = b'\x01\x02\x03\x04\x05\x06\x07\x08'
    key = b'\xff\xfe\xfd\xfc'

    masked = lomond.mask.mask(key, my_input)

    # I will explain the first two bytes, hopefully this will make the expected
    # string more clear
    # byte # | 0        | 1        | 2
    # input  | 00000001 | 00000010 | 00000011
    # mask   | 11111111 | 11111110 | 11111101
    # xor    | 11111110 | 11111100 | 11111110
    # xor-chr| \xfe     | \xfc     | \xfe
    assert masked == b'\xfe\xfc\xfe\xf8\xfa\xf8\xfa\xf4'

    # we could also did this in detail to fully explain why the bytes are this
    # and not some other:
    for i, _char in enumerate(my_input):
        input_item = six.indexbytes(my_input, i)
        key_item = six.indexbytes(key, i % 4)
        assert six.indexbytes(masked, i) == input_item ^ key_item


def test_unmasking():
    my_input = b'\xfe\xfc\xfe\xf8\xfa\xf8\xfa\xf4'
    key = b'\xff\xfe\xfd\xfc'

    output = lomond.mask.mask(key, my_input)

    # again, one example should suffice:

    # input  | 11111110
    # mask   | 11111111
    # xor    | 00000001
    # xor-chr| \x01
    assert output == b'\x01\x02\x03\x04\x05\x06\x07\x08'
