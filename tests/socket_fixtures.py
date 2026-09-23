from __future__ import unicode_literals

from base64 import b64encode
from hashlib import sha1
import socket
import select
import threading

from lomond import constants
from lomond.frame import Frame
from lomond.opcode import Opcode


def _ignore_cleanup_error():
    """Best-effort fixture teardown should never fail tests."""
    return


def get_free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _recv_until(sock, separator):
    data = b''
    while separator not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def _recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def _bytes_to_int(value):
    if not value:
        return 0
    result = 0
    for byte in bytearray(value):
        result = (result << 8) | byte
    return result


def _read_frame(sock):
    header = _recv_exact(sock, 2)
    if not header:
        return None
    byte1 = ord(header[:1]) if not isinstance(header[0], int) else header[0]
    byte2 = ord(header[1:2]) if not isinstance(header[1], int) else header[1]
    opcode = byte1 & 0x0F
    masked = bool(byte2 & 0x80)
    length = byte2 & 0x7F
    if length == 126:
        _length = _recv_exact(sock, 2)
        if _length is None:
            return None
        length = _bytes_to_int(_length)
    elif length == 127:
        _length = _recv_exact(sock, 8)
        if _length is None:
            return None
        length = _bytes_to_int(_length)
    if masked:
        if _recv_exact(sock, 4) is None:
            return None
    if length and _recv_exact(sock, length) is None:
        return None
    return opcode


def _handshake_response(request_headers):
    key = None
    for line in request_headers.split(b'\r\n'):
        if line.lower().startswith(b'sec-websocket-key:'):
            key = line.split(b':', 1)[1].strip()
            break
    if key is None:
        return None
    accept = b64encode(sha1(key + constants.WS_KEY).digest())
    response = (
        b'HTTP/1.1 101 Switching Protocols\r\n'
        b'Upgrade: websocket\r\n'
        b'Connection: Upgrade\r\n'
        b'Sec-WebSocket-Accept: ' + accept + b'\r\n'
        b'\r\n'
    )
    return response


class LocalWebSocketServer(object):
    def __init__(self, port, messages=None, close_after_messages=False):
        self.port = port
        self.messages = messages or []
        self.close_after_messages = close_after_messages
        self._server = None
        self._thread = None
        self._stopped = threading.Event()

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(('127.0.0.1', self.port))
        self._server.listen(5)
        self._server.settimeout(0.2)
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stopped.set()
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                _ignore_cleanup_error()
        if self._thread is not None:
            self._thread.join(1.0)

    def _run(self):
        while not self._stopped.is_set():
            try:
                conn, _addr = self._server.accept()
            except socket.timeout:
                continue
            except Exception:
                return
            self._handle_connection(conn)

    def _handle_connection(self, conn):
        try:
            request_headers = _recv_until(conn, b'\r\n\r\n')
            response = _handshake_response(request_headers)
            if response is None:
                return
            conn.sendall(response)

            for message_type, payload in self.messages:
                if message_type == 'text':
                    frame = Frame(Opcode.TEXT, payload.encode('utf-8'), mask=False)
                else:
                    frame = Frame(Opcode.BINARY, payload, mask=False)
                conn.sendall(frame.to_bytes())

            if self.close_after_messages:
                conn.sendall(Frame(Opcode.CLOSE, b'', mask=False).to_bytes())
                # Give the client a short window to respond with CLOSE so the
                # socket shutdown is less likely to surface as a connection
                # reset race on faster runtimes.
                try:
                    conn.settimeout(0.5)
                    _read_frame(conn)
                except Exception:
                    # The test fixture should not fail teardown if the client
                    # races socket close and no CLOSE frame is readable.
                    _ignore_cleanup_error()
                return

            while True:
                opcode = _read_frame(conn)
                if opcode is None:
                    return
                if opcode == Opcode.CLOSE:
                    conn.sendall(Frame(Opcode.CLOSE, b'', mask=False).to_bytes())
                    return
        finally:
            try:
                conn.close()
            except Exception:
                _ignore_cleanup_error()


class LocalHTTPServer(object):
    def __init__(self, port):
        self.port = port
        self._server = None
        self._thread = None
        self._stopped = threading.Event()

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(('127.0.0.1', self.port))
        self._server.listen(5)
        self._server.settimeout(0.2)
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stopped.set()
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                _ignore_cleanup_error()
        if self._thread is not None:
            self._thread.join(1.0)

    def _run(self):
        while not self._stopped.is_set():
            try:
                conn, _addr = self._server.accept()
            except socket.timeout:
                continue
            except Exception:
                return
            try:
                _recv_until(conn, b'\r\n\r\n')
                conn.sendall(
                    b'HTTP/1.1 200 OK\r\n'
                    b'Content-Type: text/plain\r\n'
                    b'Content-Length: 17\r\n'
                    b'\r\n'
                    b'not a websocket'
                )
            finally:
                conn.close()


class LocalConnectProxy(object):
    def __init__(self, port):
        self.port = port
        self._server = None
        self._thread = None
        self._stopped = threading.Event()

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(('127.0.0.1', self.port))
        self._server.listen(5)
        self._server.settimeout(0.2)
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stopped.set()
        if self._server is not None:
            try:
                self._server.close()
            except Exception:
                _ignore_cleanup_error()
        if self._thread is not None:
            self._thread.join(1.0)

    def _run(self):
        while not self._stopped.is_set():
            try:
                conn, _addr = self._server.accept()
            except socket.timeout:
                continue
            except Exception:
                return
            thread = threading.Thread(target=self._handle_connection, args=(conn,))
            thread.daemon = True
            thread.start()

    def _handle_connection(self, client):
        upstream = None
        try:
            request = _recv_until(client, b'\r\n\r\n')
            first_line = request.split(b'\r\n', 1)[0]
            parts = first_line.split()
            if len(parts) < 2 or parts[0] != b'CONNECT':
                client.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                return
            host_port = parts[1].decode('ascii', 'replace')
            host, port = host_port.rsplit(':', 1)
            upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            upstream.connect((host, int(port)))
            client.sendall(
                b'HTTP/1.1 200 Connection established\r\n'
                b'Connection: keep-alive\r\n'
                b'\r\n'
            )
            sockets = [client, upstream]
            while True:
                readable, _, _ = select.select(sockets, [], [], 0.2)
                if not readable:
                    if self._stopped.is_set():
                        return
                    continue
                for source in readable:
                    data = source.recv(4096)
                    if not data:
                        return
                    if source is client:
                        upstream.sendall(data)
                    else:
                        client.sendall(data)
        finally:
            try:
                client.close()
            except Exception:
                _ignore_cleanup_error()
            if upstream is not None:
                try:
                    upstream.close()
                except Exception:
                    _ignore_cleanup_error()
