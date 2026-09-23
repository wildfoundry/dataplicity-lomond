from __future__ import unicode_literals

import pytest
import time

from lomond import WebSocket, proxy
from socket_fixtures import get_free_port, LocalWebSocketServer, LocalConnectProxy


@pytest.fixture(scope='module')
def ws_url():
    port = get_free_port()
    server = LocalWebSocketServer(port)
    server.start()
    time.sleep(0.05)
    yield 'ws://127.0.0.1:{}/echo'.format(port)
    server.stop()


def test_build_request():
    request_bytes = proxy.build_request(
        'ws://example.org', 8888, proxy_username='foo'
    )
    expected = (
        b'CONNECT ws://example.org:8888 HTTP/1.1\r\n'
        b'Host: ws://example.org\r\n'
        b'Proxy-Connection: keep-alive\r\n'
        b'Connection: keep-alive\r\n'
        b'Proxy-Authorization: Basic Zm9v\r\n\r\n'
    )
    assert request_bytes == expected


def test_parser():
    response_lines = [
        b'HTTP/1.1 200 Connection established\r\n',
        b'foo: bar\r\n',
        b'\r\n',
    ]
    proxy_parser = proxy.ProxyParser()
    for line in response_lines:
        for response in proxy_parser.feed(line):
            break

    assert response.status == 'Connection established'
    assert response.status_code == 200
    assert response.headers['foo'] == 'bar'


def test_parser_fail():
    """Test non-success response from proxy."""
    response_lines = [
        b'HTTP/1.1 407 auth required\r\n',
        b'foo: bar\r\n\r\n'
    ]
    proxy_parser = proxy.ProxyParser()
    with pytest.raises(proxy.ProxyFail):
        for line in response_lines:
            for _parsed_response in proxy_parser.feed(line):
                break


def test_parser_fail_nodata():
    """Test no response from proxy."""
    proxy_parser = proxy.ProxyParser()
    with pytest.raises(proxy.ProxyFail):
        for response in proxy_parser.feed(b''):
            break


def test_proxy(ws_url):
    proxy_port = get_free_port()
    proxy_server = LocalConnectProxy(proxy_port)
    proxy_server.start()
    proxy_url = 'http://127.0.0.1:{}'.format(proxy_port)
    try:
        ws = WebSocket(
            ws_url,
            proxies={'http': proxy_url}
        )
        _events = []
        for event in ws:
            _events.append(event)
            if event.name == 'ready':
                ws.close()

        assert len(_events) == 6
        assert _events[0].name == 'connecting'
        assert _events[1].name == 'connected'
        assert _events[1].proxy == proxy_url
        assert _events[2].name == 'ready'
        assert _events[3].name == 'poll'
        assert _events[4].name == 'closed'
        assert _events[5].name == 'disconnected'
    finally:
        proxy_server.stop()


def test_bad_proxy(ws_url):
    bad_proxy_port = get_free_port()
    ws = WebSocket(
        ws_url,
        proxies={'http': 'http://127.0.0.1:{}'.format(bad_proxy_port)}
    )
    _events = list(ws.connect())
    assert len(_events) == 2
    assert _events[0].name == 'connecting'
    assert _events[1].name == 'connect_fail'
