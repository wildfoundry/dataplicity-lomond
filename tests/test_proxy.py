from lomond.proxy import ProxyInfo
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
