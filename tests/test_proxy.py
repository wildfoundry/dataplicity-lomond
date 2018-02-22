from lomond.proxy import issue_proxy_connect
from lomond.proxy import ProxyConnectionError
from lomond.proxy import ProxyInfo
from test_session import FakeSocket

import pytest


proxy_info_parse_ok = [
    (
        None,
        ProxyInfo(host=None, port=None, credentials=None)
    ),
    (
        'http://a-proxy.com',
        ProxyInfo(host='a-proxy.com', port=80, credentials=None)
    ),
    (
        'http://a-proxy.com:8080/',
        ProxyInfo(host='a-proxy.com', port=8080, credentials=None)
    ),
    (
        'http://jdoe@a-proxy.com',
        ProxyInfo(host='a-proxy.com', port=80, credentials=b'jdoe')
    ),
    (
        'http://jdoe@a-proxy.com:8080',
        ProxyInfo(host='a-proxy.com', port=8080, credentials=b'jdoe')
    ),
    (
        'http://jdoe:qwerty@a-proxy.com:8080/',
        ProxyInfo(host='a-proxy.com', port=8080, credentials=b'jdoe:qwerty')
    ),
    (
        'a-proxy.com:8888',
        ProxyInfo(host='a-proxy.com', port=8888, credentials=None)
    ),
    (
        'a-proxy.com',
        ProxyInfo(host='a-proxy.com', port=80, credentials=None)
    ),
    (
        'jdoe@a-proxy.com',
        ProxyInfo(host='a-proxy.com', port=80, credentials=b'jdoe')
    ),
]

@pytest.mark.parametrize("proxy_url, expected", proxy_info_parse_ok)
def test_proxy_info_parse_ok(proxy_url, expected):
    result = ProxyInfo.parse(proxy_url)
    assert  result == expected


proxy_info_parse_failure = [
    ('https://a-proxy.com/', 'illegal proxy scheme'),
    ('http://a-proxy.com:a-port/', 'illegal proxy port value'),
    ('http://a-proxy.com/foo', 'illegal proxy url'),
    ('http://a-proxy.com/?foo=bar', 'illegal proxy url'),
    ('http:///', 'illegal proxy url'),
    ('http://:8080/', 'illegal proxy url'),
]


@pytest.mark.parametrize("proxy_url, expected", proxy_info_parse_failure)
def test_proxy_info_parse_failure(proxy_url, expected):
    with pytest.raises(ValueError) as e_info:
        ProxyInfo.parse(proxy_url)

    assert e_info.value.args == (expected,)


def test_issue_proxy_connect_no_credentials():
    expected_request = (
        b'CONNECT foo.com:80 HTTP/1.1\r\n'
        b'Host: foo.com\r\n'
        b'Proxy-Connection: keep-alive\r\n'
        b'Connection: keep-alive\r\n'
        b'\r\n'
    )
    proxy_sock = FakeSocket(
        recv_buffer=(
            b'HTTP/1.0 200 Connection established\r\n'
            b'Some-header: Yeah\r\n'
            b'Another-header: Why not\r\n'
            b'\r\n'
        )
    )
    issue_proxy_connect(proxy_sock, 'foo.com', 80, credentials=None)
    assert proxy_sock.send_buffer == expected_request
    assert proxy_sock.recv_buffer == b''


def test_issue_proxy_connect_credentials():
    credentials = b"Aladdin:open sesame"  # example taken from RFC-7617
    expected_request = (
        b'CONNECT foo.com:80 HTTP/1.1\r\n'
        b'Host: foo.com\r\n'
        b'Proxy-Connection: keep-alive\r\n'
        b'Connection: keep-alive\r\n'
        b'Proxy-Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==\r\n'
        b'\r\n'
    )
    proxy_sock = FakeSocket(
        recv_buffer=(
            b'HTTP/1.0 200 Connection established\r\n'
            b'About-your-credentials: Loved them\r\n'
            b'\r\n'
        )
    )
    issue_proxy_connect(proxy_sock, 'foo.com', 80, credentials=credentials)
    assert proxy_sock.send_buffer == expected_request
    assert proxy_sock.recv_buffer == b''



proxy_error_cases = [
    (
        'Bad response (empty)',
        b''
    ),
    (
        'Bad response (line error)',
        b'HTTP/1.0 200 Connection established\r\n'
    ),
    (
        'Bad response (line error)',
        b'HTTP/1.0 200 Connection established\r\n'
        b'Some-Head'
    ),
    (
        'Bad response (status)',
        b'220 smtp.server.com Simple Mail Transfer Service Ready\r\n'
    ),
    (
        ('418', "I'm a teapot"),
        b'HTTP/1.0 418 I\'m a teapot\r\n'
    ),
    (
        'Bad response (line too long)',
        b'HTTP/1.0 200 Connection established%s\r\n'
        b'\r\n' % b''.join([b'!'] * 4096)
    ),
    (
        'Bad response (line too long)',
        b'HTTP/1.0 200 Connection established\r\n'
        b'GNU: %s...\r\n'
        b'\r\n' % b''.join([b'GNU is not unix -> '] * 218)
    ),
    (
        'Bad response (header too long)',
        b'HTTP/1.0 200 Connection established\r\n'
        b'%s'
        b'\r\n' % b'\r\n'.join(b'Header-%d: Stuff' % i for i in range(128))
    )
]

@pytest.mark.parametrize("expected_error, response", proxy_error_cases)
def test_issue_proxy_error_handling(response, expected_error):
    if not isinstance(expected_error, tuple):
        expected_error = (expected_error,)

    proxy_sock = FakeSocket(recv_buffer=response)
    with pytest.raises(ProxyConnectionError) as e_info:
        issue_proxy_connect(proxy_sock, 'foo.com', 80, credentials=None)

    assert e_info.value.args == expected_error
