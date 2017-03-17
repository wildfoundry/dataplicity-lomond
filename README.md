# Dataplicity Lomond

Tranquil WebSockets.

Lomond is a Websocket client which turns a websocket connection in to
an orderly stream of _events_. Contrast this with the existing websocket
clients available for Python which follow a more JS-like model of
threads and callbacks.


## How to Use

First construct a `WebSocket` object, then call the `connect` method,
which will return a generator of websocket events.

To run the websocket, simply iterate over the returned generator. You may
do this an another thread, but it isn't required.


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
│ Binary / Text ─ Poll │──┘  application data
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


## Example

The following is a silly example that connects to a websocket server
(in this case a public echo server), and sends a string of text
every 5 seconds.


```python
from lomond import WebSocket

ws = WebSocket('wss://echo.websocket.org')
for event in ws:
    if event.name == 'poll':
        ws.send_text('Hello, World')
    elif event.name == 'text':
        print(event.text)
```



