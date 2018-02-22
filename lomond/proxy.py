"""
Http proxy support
"""

from __future__ import print_function
from __future__ import unicode_literals

import base64
from collections import namedtuple

import six
from six.moves import range
from six.moves.urllib.parse import urlparse


class ProxyInfo(namedtuple('ProxyInfo', 'host port credentials')):
    __slots__ = ()

    @classmethod
    def parse(cls, proxy_url):
        host, port, credentials = [None] * 3
        if proxy_url:
            _url = urlparse(proxy_url, allow_fragments=False)
            if not _url.scheme:
                assert not _url.netloc, _url
                netloc, slash, path = _url.path.partition('/')
                path = slash + path
            elif _url.scheme == 'http':
                netloc = _url.netloc
                path = _url.path
            else:
                raise ValueError('illegal proxy scheme')

            if '@' in netloc:
                credentials, _, host_port = netloc.partition('@')
                if isinstance(credentials, six.text_type):
                    credentials = credentials.encode('ascii')
            else:
                host_port = netloc

            host, _, port_str = host_port.partition(':')

            if port_str and not port_str.isdigit():
                raise ValueError('illegal proxy port value')
            port = int(port_str or '80')

            invalid_path = path not in ['', '/']
            if not host or invalid_path or _url.params or _url.query:
                raise ValueError('illegal proxy url')

        return cls(host=host, port=port, credentials=credentials)


class ProxyConnectionError(Exception):
    """
    Raised due to issues while dealing with the proxy
    """


def issue_proxy_connect(proxy_sock, target_host, target_port, credentials=None):
    """
    Takes a socket connected to a proxy and issues a `CONNECT` request,
    processing the response afterwards.
    If `credentials` is provided, it will be base64-encoded and passed as
    Basic authentication (so it should be of the form `user:password`)
    """

    request = [
        'CONNECT %s:%d HTTP/1.1' % (target_host, target_port),
        'Host: %s' % target_host,
        'Proxy-Connection: keep-alive',
        'Connection: keep-alive',
    ]

    if credentials:
        base64_credentials = base64.standard_b64encode(credentials).decode('ascii')
        request.append('Proxy-Authorization: Basic %s' % base64_credentials)

    request.append('\r\n')

    encoded_request = '\r\n'.join(request).encode('utf-8')
    proxy_sock.sendall(encoded_request)

    response = read_line(proxy_sock, is_first_line=True)
    protocol_version, status_code, message = response.split(' ', 2)

    if not protocol_version.startswith('HTTP/'):
        raise ProxyConnectionError('Bad response (status)')

    if status_code != '200':
        raise ProxyConnectionError(status_code, message)


    response_headers = []
    for _ in range(128):
        line = read_line(proxy_sock)
        if line:
            response_headers.append(line)
        else:
            break
    else:
        # Too many headers?
        raise ProxyConnectionError('Bad response (header too long)')


def read_line(sock, is_first_line=False):
    buf = []
    for _ in range(4096):
        c = sock.recv(1)
        buf.append(c)
        if not c or c == b'\n':
            break
    else:
        # Line suspiciously long...
        raise ProxyConnectionError('Bad response (line too long)')

    result = b''.join(buf)

    if not result and is_first_line:
        raise ProxyConnectionError('Bad response (empty)')
    if not result.endswith(b'\r\n'):
        raise ProxyConnectionError('Bad response (line error)')
    return result.rstrip().decode('utf-8')
