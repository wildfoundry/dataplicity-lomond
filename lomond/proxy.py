from __future__ import unicode_literals

import base64

from .errors import ProxyError
from .parser import Parser
from .response import Response


class ProxyResponse(Response):
    """The response received from the proxy."""


class ProxyParser(Parser):
    """Parser for communication with a SOCKS proxy."""

    def build_request(self, host, port, credentials=None):
        """Build a request to the proxy."""
        request = [
            b'CONNECT {}:{} HTTP/1.1'.format(host, port).encode('utf-8')
        ],
        headers = [
            (b'Host', host.encode('utf-8')),
            (b'Proxy-Connection', b'keep-alive'),
            (b'Connection', b'keep-alive'),
        ]

        if credentials:
            _credentials = credentials.encode('utf8')
            b64_credentials = base64.standard_b64encode(_credentials)
            headers.append(
                (b'Proxy-Authorization:', 'Basic ' + b64_credentials)
            )

        for header, value in headers:
            request.append(header + b': ' + value)

        request.append(b'\r\n')
        request_bytes = b'\r\n'.join(request)
        return request_bytes

    def parse(self):
        headers_data = yield self.read_until(b'\r\n', max_bytes=16 * 1024)
        response = ProxyResponse(headers_data)
        if response.status_code != 200:
            raise ProxyError(
                'proxy error; {} {}',
                response.status_code,
                response.status
            )
        yield response