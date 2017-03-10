from __future__ import print_function
from __future__ import unicode_literals

from collections import deque
import select
import socket
import threading
import time

import six

from .frame import Frame
from . import events


class WebsocketSession(object):

    def __init__(self, websocket, reconnect=True):
        self.websocket = websocket
        self.reconnect = reconnect
        self._address = (websocket.host, websocket.port)
        self._lock = threading.Lock()

        self._sock = None
        self.url = websocket.url
        self._write_buffer = deque()
        self._sent_close = False

    def __repr__(self):
        return "<ws-session '{}'>".format(self.url)

    def write(self, data, flush=True):
        """Send raw data."""
        # TODO: split large packets?
        self._write_buffer.append(data)
        if flush:
            self.flush()

    def send(self, opcode, data):
        """Send a WS Frame."""
        frame = Frame(opcode, payload=data)
        self.write(frame.to_bytes())

    def _select(self, sock, poll):
        return select.select(
            [sock],
            [sock] if self._write_buffer else [],
            [sock],
            poll
        )

    def flush(self):
        with self._lock:
            sock = self._sock
            while self._write_buffer:
                data = self._write_buffer.popleft()
                sent = sock.send(data)
                if sent != len(data):
                    self._write_buffer.appendleft(data[sent:])

    def _make_socket(self):
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )
        return sock

    def events(self, poll=15):
        # TODO: implement exponential back off
        websocket = self.websocket

        while 1:
            yield events.Connecting(websocket.url)
            try:
                sock = self._sock = self._make_socket()
                sock.connect(self._address)
            except socket.error as error:
                yield events.ConnectFail(six.text_type(error))
                time.sleep(5)
                continue
            else:
                break

        yield events.Connected(websocket.url)
        websocket.send_request()

        poll_start = time.time()
        while not websocket.is_closed:
            try:
                reads, writes, errors = self._select(sock, poll)
            except KeyboardInterrupt:
                websocket.close(1000, 'goodbye')
                continue
            if writes:
                self.flush()
            if reads:
                try:
                    data = sock.recv(4096)
                except socket.error:
                    break
                if not data:
                    break
                for event in websocket.feed(data):
                    yield event
            if errors:
                break
            current_time = time.time()
            if current_time - poll_start > poll:
                poll_start = current_time
                yield events.Poll()

        yield events.Disconnected()
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except socket.error:
            pass
        else:
            sock = None


if __name__ == "__main__":

    # Test with wstest -m echoserver -w ws://127.0.0.1:9001 -d
    # Get wstest app from http://autobahn.ws/testsuite/

    from .websocket import WebSocket

    ws = WebSocket('ws://127.0.0.1:9001')
    for event in ws.connect(poll=5):
        print(event)
        if isinstance(event, events.Poll):
            ws.send_text('Hello, World')
            ws.send_binary(b'hello world in binary')

