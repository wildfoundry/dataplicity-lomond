# Dataplicity Lomond

Tranquil WebSockets for Python.

[![PyPI version](https://badge.fury.io/py/fs.svg)](https://pypi.org/project/lomond/)
[![PyPI](https://img.shields.io/pypi/pyversions/lomond.svg)](https://pypi.org/project/lomond/)

Lomond is a Websocket client which turns a websocket connection in to
an orderly stream of _events_. No threads or callbacks necessary.

- [Documentation](https://lomond.readthedocs.io/)

- [Blog](https://www.willmcgugan.com/search/?s=lomond)

## How to Use

To connect to a "ws:" or "wss:" WebSocket URL, construct a `WebSocket` object then iterate over it. This will yield an _event object_ for each step in the connection process and for any data sent by the server.

You will receive a ``Binary`` or ``Text`` event when the server sends you a message.
You may _send_ a message with the ``send_binary`` or ``send_text`` methods.

## Example

The following is a silly example that connects to a websocket server
(in this case a public echo server), and sends a string of text
every 5 seconds.


```python
from lomond import WebSocket


websocket = WebSocket('wss://echo.websocket.org')

for event in websocket:
    if event.name == 'poll':
        websocket.send_text('Hello, World')
    elif event.name == 'text':
        print(event.text)
```


## Events

A successful websocket connection will result in a series of events
such as the following:

```
┌──────────────────────┐
│      Connecting      │     Contacting server
└──────────────────────┘
           │
           ▼
┌──────────────────────┐     Connected to server (but
│      Connected       │     not yet sent data)
└──────────────────────┘
           │
           ▼
┌──────────────────────┐     Negotiated Websocket
│        Ready         │     handshake
└──────────────────────┘
           │  ┌───────────┐
           │  │           │
           ▼  ▼           │
┌──────────────────────┐  │  Send and receive
│ Binary / Text / Poll │──┘  application data
└──────────────────────┘
           │
           ▼
┌──────────────────────┐     Websocket close
│        Closed        │     handshake
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│     Disconnected     │     Disconnected TCP/IP
└──────────────────────┘     connection to server
```
