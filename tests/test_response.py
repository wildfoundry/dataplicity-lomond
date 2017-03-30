from lomond.response import Response
import pytest


def test_constructor():
    r = Response(b'\r\n')

    assert isinstance(r, Response)


def test_parsing_of_headers():
    headers = (b'GET HTTP/1.1\r\nContent-Type:ascii\r\n'
               b'Array:Item-1\r\nArray:Item-2\r\n\r\n')

    r = Response(headers)

    assert r.get(b'content-type') == b'ascii'
    assert r.get(b'array') == b'Item-1,Item-2'
    assert r.get_list(b'array') == ['Item-1', 'Item-2']
    assert r.get_list(b'no-such-header') == []
    assert r.get(b'no-such-header') is None


def test_header_name_must_be_passed_as_bytes():
    headers = b'GET HTTP/1.1\r\nHeader:value\r\n\r\n'
    r = Response(headers)

    with pytest.raises(Exception):
        r.get(u'header')


def test_repr():
    r = Response(b'HTTP/1.1 418 OK')
    assert repr(r) == '<response HTTP/1.1 418 OK>'
