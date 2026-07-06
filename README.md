# Dataplicity Lomond

Tranquil WebSockets for Python.

[![PyPI version](https://badge.fury.io/py/lomond.svg)](https://pypi.org/project/lomond/)
[![PyPI](https://img.shields.io/pypi/pyversions/lomond.svg)](https://pypi.org/project/lomond/)
[![Coverage Status](https://coveralls.io/repos/github/wildfoundry/dataplicity-lomond/badge.svg?branch=master)](https://coveralls.io/github/wildfoundry/dataplicity-lomond?branch=master)
[![CircleCI](https://circleci.com/gh/wildfoundry/dataplicity-lomond/tree/master.svg?style=svg)](https://circleci.com/gh/wildfoundry/dataplicity-lomond/tree/master)

Lomond is a Websocket client which turns a websocket connection in to
an orderly stream of _events_. No threads or callbacks necessary.

- [Documentation](https://lomond.readthedocs.io/)

- [GitHub Repository](https://github.com/wildfoundry/dataplicity-lomond)

- [Blog](https://www.willmcgugan.com/search/?s=lomond)

## How to Use

To connect to a "ws:" or "wss:" WebSocket URL, construct a `lomond.WebSocket` object then iterate over it. This will yield an _event object_ for each step in the connection process and for any data sent by the server.

You will receive a ``Binary`` or ``Text`` event when the server sends you a message.
You may _send_ a message with the ``send_binary`` or ``send_text`` methods.

## TLS and Debugging

`wss://` connections now verify TLS certificates by default. You can tune this
without changing global SSL behavior:

```python
ws = WebSocket(
    "wss://example.com/socket",
    ssl_verify=True,                 # default
    ssl_cafile="/etc/ssl/my-ca.pem", # optional custom CA bundle
)
```

For deep diagnostics, pass a trace callback and Lomond will emit structured
records for connect, handshake, send/recv, and close stages:

```python
def on_trace(record):
    print(record)

ws = WebSocket("wss://example.com/socket", trace=on_trace)
```

`lomond.persist.persist()` now also supports `Retry-After` from rejected
upgrade responses (for example, `429 Too Many Requests`) and will use that
delay before reconnecting when present.

## Testing and CI

The test suite now uses deterministic local socket fixtures for websocket,
HTTP, and proxy scenarios (no public network dependencies required).

Modern CI runs on Python 3.8 through 3.13, and a separate legacy CI lane
runs Python 2.7, 3.5, 3.6, and 3.7 in GitHub-hosted Docker jobs.

Developers do not need Docker locally to validate day-to-day changes; full
legacy coverage is enforced in GitHub Actions.

## PyPI Trusted Publisher (TPM)

This repository is configured to publish to PyPI via GitHub Actions OIDC
Trusted Publishing with no API token.

Workflow file:

- `.github/workflows/pypi-publish.yml`

PyPI Trusted Publisher form values:

- **Owner**: `wildfoundry`
- **Repository name**: `dataplicity-lomond`
- **Workflow name**: `pypi-publish.yml`
- **Environment name**: `release`

Before first release, create the GitHub environment named `release` in the
repository settings.

Publishing behavior:

- Push a version tag matching `v*` (for example `v0.3.3`) to trigger publish.
- You can also run the workflow manually via `workflow_dispatch`.

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
