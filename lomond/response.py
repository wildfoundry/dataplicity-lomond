"""
A simple abstraction for an HTTP response.

A response object is supplied in the :class:`~lomond.events.Ready`
event.

"""


from __future__ import unicode_literals

from collections import defaultdict


class Response(object):
    """A HTTP response.

    :param bytes header_data: Raw response.

    """

    def __init__(self, header_data):
        self.raw = header_data
        lines = iter(header_data.split(b'\r\n'))
        status_line = next(lines, b'')
        tokens = iter(status_line.split(None, 2))
        self.http_ver = next(tokens, b'').decode('utf-8', errors='replace')
        try:
            self.status_code = int(next(tokens, b''))
        except ValueError:
            self.status_code = None
        self.status = next(tokens, b'').decode('utf-8', errors='replace')

        headers = defaultdict(list)
        for line in lines:
            if line.strip():
                header, _, value = line.partition(b':')
                header = header.lower().strip()
                value = value.strip()
                headers[header].append(value)

        self.headers = {
            header: b','.join(value)
            for header, value in headers.items()
        }

    def __repr__(self):
        return "<response {} {} {}>".format(
            self.http_ver,
            self.status_code,
            self.status
        )

    def get(self, name, default=None):
        """Get a header.

        :param bytes name: Name of the header to retrieve.
        :param default: Default value if header is not present.
        :rtype: bytes

        """
        assert isinstance(name, bytes), "must be bytes"
        return self.headers.get(name.lower(), default)

    def get_list(self, name):
        """Extract a list from a header.

        :param bytes name: Name of the header to retrieve.

        :rtype: list
        :returns: A list of strings in the header.

        """
        value = self.get(name, b'').decode('utf-8', errors='replace')
        if not value.strip():
            return []
        parts = [part.strip() for part in value.split(',')]
        return parts
