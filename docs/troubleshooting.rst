Troubleshooting
===============

This guide focuses on diagnosing production connection issues quickly.

Trace Cookbook
--------------

Enable structured tracing by passing a callback to ``WebSocket(trace=...)``.

.. code-block:: python

    from lomond import WebSocket

    def on_trace(record):
        print(record)

    ws = WebSocket("wss://example.com/socket", trace=on_trace)
    for event in ws.connect():
        pass

Trace records include:

- ``connect_start``: connection loop settings
- ``tls_wrapped``: TLS wrapping path and verification mode
- ``handshake_ready`` / ``handshake_rejected``: upgrade result
- ``socket_send`` / ``socket_recv``: transport throughput
- ``close_requested`` / ``disconnected``: shutdown sequence

Common Failure Signatures
-------------------------

``ConnectFail(reason='unable to connect; ...')``
    DNS, routing, firewall, or proxy connectivity issue.

``Rejected(..., reason='Websocket upgrade failed (code=...)')``
    Server responded with non-``101`` HTTP status. Check endpoint path,
    authentication, and reverse proxy upgrade configuration.

``ProtocolError(..., critical=True)``
    Invalid wire data (often invalid UTF-8 in text frames). Peer is sending
    malformed payloads.

``Disconnected(reason='socket fail; ...', graceful=False)``
    Transport dropped unexpectedly. Inspect network stability and keepalive
    settings.

``Unresponsive``
    No pong arrived within ``ping_timeout``. Increase timeout or inspect peer
    responsiveness.

Retry Strategy Diagnostics
--------------------------

When using ``persist()``, reconnect waits are selected in this order:

1. ``Retry-After`` header from rejected handshake responses (if present and
   ``respect_retry_after=True``)
2. Exponential randomized backoff between ``min_wait`` and ``max_wait``

Each wait is emitted as a ``BackOff`` event for observability.
