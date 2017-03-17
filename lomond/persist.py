"""
Maintains a persistent websocket connection.

"""

from __future__ import unicode_literals

from random import random
import threading

from . import events


def persist(websocket, poll=5,
            min_wait=5, max_wait=30,
            ping_rate=30, retry_event=None):
    """Run a websocket, with a retry mechanism and exponential back-off."""
    if retry_event is None:
        retry_event = threading.Event()
    retries = 0
    random_wait = max_wait - min_wait
    while True:
        retries += 1
        for event in websocket.connect(poll=poll, ping_rate=ping_rate):
            if event.name == 'ready':
                # The server accepted the WS upgrade.
                retries = 0
            yield event
        wait_for = min_wait + random() * min(random_wait, 2**retries)
        yield events.BackOff(wait_for)
        if retry_event.wait(wait_for):
            break


if __name__ == "__main__":
    # Test with wstest -m broadcastserver -w ws://127.0.0.1:9001 -d

    from .websocket import WebSocket

    ws = WebSocket('ws://127.0.0.1:9001/')
    for event in persist(ws):
        print(event)
        if isinstance(event, events.Poll):
            ws.send_text('Hello, World')
            ws.send_binary(b'hello world in binary')
            ws.send_ping(b'test')

