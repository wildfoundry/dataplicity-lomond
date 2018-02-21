"""
Http proxy support
"""

from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple

import six
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
