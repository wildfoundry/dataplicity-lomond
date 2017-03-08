from __future__ import print_function
from __future__ import unicode_literals

from collections import deque
from .frame import Frame
import select
import socket
import time

import six

from .websocket import WebSocket

from . import events


class WebsocketSession(object):

    def __init__(self, websocket, reconnect=True):
        self.websocket = websocket
        self.reconnect = reconnect
        self._address = (websocket.host, websocket.port)

        self._sock = None
        self.url = websocket.url
        self._write_buffer = deque()
        self._sent_close = False

    def __repr__(self):
        return "<ws-session '{}'>".format(self.url)

    def _write(self, data):
        # TODO: split large packets?
        self._write_buffer.append(data)

    def send(self, opcode, data):
        frame = Frame(opcode, payload=data)
        self._write(frame.to_bytes())

    def send_binary(self, data):
        frame_bytes = Frame.build_binary(data)
        self._write(frame_bytes)

    def send_text(self, text):
        frame_bytes = Frame.build_text(text)
        self._write(frame_bytes)

    def send_close(self, code, reason):
        frame_bytes = Frame.build_close(code, reason)
        self._write(frame_bytes)
        self._sent_close = True

    def send_request(self):
        request = self.websocket.get_request()
        self._write(request)

    def on_close(message):
        pass

    def _select(self, sock, poll):
        return select.select(
            [sock],
            [sock] if self._write_buffer else [],
            [sock],
            poll
        )

    def flush(self):
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
        while True:
            yield self, events.Connecting()
            try:
                sock = self._make_socket()
                sock.connect(self._address)
            except socket.error as error:
                yield self, events.ConnectFail(six.text_type(error))
                time.sleep(5)
                continue

            yield self, events.Connected()
            self.send_request()

            poll_start = time.time()
            while True:
                reads, writes, errors = self._select(sock, poll)
                if errors:
                    break
                if writes:
                    self.flush()
                if reads:
                    data = sock.recv(4096)
                    if not data:
                        break
                    for event in websocket.feed(data, self):
                        yield self, event

                current_time = time.time()
                if current_time - poll_start > poll:
                    poll_start = current_time
                    yield self, events.Poll()


if __name__ == "__main__":

    # Test with wstest -m echoserver -w ws://127.0.0.1:9001 -d

    from .websocket import WebSocket

    websocket = WebSocket('ws://127.0.0.1:9001')
    session = websocket.connect()
    for session, event in session.events(poll=5):
        print("{} : {}".format(session, event))
        if isinstance(event, events.Poll):
            session.send_text('Hello, World')
            session.send_binary(b'hello world in binary')

