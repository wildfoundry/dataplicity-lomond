from __future__ import unicode_literals

import pytest

from lomond import proxy
from lomond.errors import ProxyFail


def test_build_request():
    request_bytes = proxy.build_request(
        'ws://example.org', 8888, proxy_username='foo'
    )
    expected = (
        b'CONNECT ws://example.org:8888 HTTP/1.1\r\n'
        b'Host: ws://example.org\r\n'
        b'Proxy-Connection: keep-alive\r\n'
        b'Connection: keep-alive\r\n'
        b'Proxy-Authorization:: Basic Zm9v\r\n\r\n'
    )
    assert request_bytes == expected


def test_parser():
    response = [
        b'HTTP/1.1 200 Connection established\r\n',
        b'foo: bar\r\n',
        b'\r\n',
    ]
    proxy_parser = proxy.ProxyParser()
    for line in response:
        for response in proxy_parser.feed(line):
            break

    assert response.status == 'Connection established'
    assert response.status_code == 200
    assert response.headers[b'foo'] == b'bar'


def test_parser_fail():
    response = [
        b'HTTP/1.1 407 auth required\r\n',
        b'foo: bar\r\n\r\n'
    ]
    proxy_parser = proxy.ProxyParser()
    with pytest.raises(ProxyFail):
        for line in response:
            for response in proxy_parser.feed(line):
                break
