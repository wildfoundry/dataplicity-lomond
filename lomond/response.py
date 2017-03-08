"""
A simple abstraction for an HTTP response.

"""


from __future__ import unicode_literals

from collections import defaultdict


class Response(object):
    """The status line + headers."""

    def __init__(self, header_data):
        lines = iter(header_data.split(b'\r\n'))
        status_line = next(lines, b'')
        tokens = iter(status_line.split(None, 3))
        self.http_ver = next(tokens, b'').decode(errors='replace')
        try:
            self.status_code = int(next(tokens, b''))
        except ValueError:
            self.status_code = None
        self.status = next(tokens, b'').decode(errors='replace')

        headers = defaultdict(list)
        for line in lines:
            if line:
                header, _, value = line.partition(b':')
                header = header.lower().strip()
                value = value.strip()
                headers[header].append(value)

        self.headers = {
            header: b','.join(value)
            for header, value in headers.items()
        }

    def __repr__(self):
        return "{} {} {}".format(
            self.http_ver,
            self.status_code,
            self.status
        )

    def get(self, name, default=None):
        """Get a header."""
        assert isinstance(name, bytes), "must be bytes"
        return self.headers.get(name.lower(), default)

    def get_list(self, name):
        """Extract a list from a header."""
        value = self.get(name, b'').decode(errors='replace')
        parts = [part.strip() for part in value.split(',')]
        return parts

