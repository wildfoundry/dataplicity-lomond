"""
A simple abstraction for http headers.

"""


from __future__ import unicode_literals

from collections import defaultdict


class Headers(object):
    """Technically the status line + headers."""

    def __init__(self, header_data):
        lines = iter(header_data.split(b'\r\n'))
        status_line = next(lines, b'')
        tokens = iter(status_line.split(None, 3))
        self.http_ver = next(tokens, b'')
        try:
            self.status_code = int(next(tokens, b''))
        except ValueError:
            self.status_code = None
        self.status = next(tokens, b'')

        headers = defaultdict(list)
        for line in lines:
            header, _, value = line.partition(b':')
            header = header.decode(errors='replace')
            value = value.decode(errors='replace')
            headers[header].append(value)

        self._headers = {
            header: ','.join(value)
            for header, value in headers.items()
        }

    def __repr__(self):
        text = [
            "{} {} {}".format(
                self.http_ver,
                self.status_code,
                self.status
            )
        ]
        for header, value in self._headers.items():
            text.append("{}:{}".format(header, value))
        return '\n'.join(text)


    def __contains__(self, name):
        return name in self._headers

    def get(self, name, default=None):
        return self._headers.get(name, default)
