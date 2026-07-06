"""
Maintains a persistent websocket connection.

"""

from __future__ import unicode_literals

from email.utils import mktime_tz, parsedate_tz
from random import random
import threading
import time

from . import events


def _parse_retry_after(value):
    """Parse a Retry-After header value to seconds."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        retry_after = float(value)
    except ValueError:
        parsed = parsedate_tz(value)
        if parsed is None:
            return None
        retry_after = mktime_tz(parsed) - time.time()
    if retry_after < 0:
        return 0.0
    return retry_after


def persist(websocket, poll=5,
            min_wait=5, max_wait=30,
            ping_rate=30, ping_timeout=None,
            exit_event=None,
            respect_retry_after=True):
    """Run a websocket, with a retry mechanism and exponential back-off.

    :param websocket: A :class:`~lomond.websocket.Websocket` instance.
    :param float poll: The websocket poll rate, in seconds.
    :param float min_wait: The minimum time to wait between reconnect
        attempts (seconds).
    :param float max_wait: The maximum time to wait between reconnect
        attempts (seconds).
    :param float ping_rate: Delay between pings (seconds), or `0` for no
        auto ping.
    :param float ping_timeout: Maximum time in seconds to wait for a
        pong response before disconnecting. Set to `None` (default) to
        disable. If set, double `ping_rate` would be a good starting
        point.
    :param exit_event: A threading event object, which can be used to
        exit the persist loop if it is set. Set to `None` to use an
        internal event object.
    :param bool respect_retry_after: If ``True`` (default), respect
        ``Retry-After`` headers on rejected upgrade responses.

    """
    if exit_event is None:
        exit_event = threading.Event()
    retries = 0
    random_wait = max_wait - min_wait
    while True:
        retries += 1
        retry_after = None
        for event in websocket.connect(
                poll=poll, ping_rate=ping_rate, ping_timeout=ping_timeout):
            if event.name == 'ready':
                # The server accepted the WS upgrade.
                retries = 0
            elif respect_retry_after and event.name == 'rejected':
                response = getattr(event, 'response', None)
                if response is not None:
                    retry_after = _parse_retry_after(response.get('retry-after'))
            yield event
        if retry_after is None:
            wait_for = min_wait + random() * min(random_wait, 2**retries)
        else:
            wait_for = retry_after
        yield events.BackOff(wait_for)
        if exit_event.wait(wait_for):
            break


if __name__ == "__main__":  # pragma: no cover
    # Test with wstest -m broadcastserver -w ws://127.0.0.1:9001 -d

    from .websocket import WebSocket

    ws = WebSocket('ws://127.0.0.1:9001/')
    for event in persist(ws):
        print(event)
        if isinstance(event, events.Poll):
            ws.send_text('Hello, World')
            ws.send_binary(b'hello world in binary')
            ws.send_ping(b'test')
