Guide
=====


Installing
----------

You can install PyFilesystem with ``pip`` as follows::

    pip install lomond

Or to upgrade to the most recent version::

    pip install lomond --upgrade

Alternatively, if you would like to install from source, you can check
out `the code from Github <https://github.com/wildfoundry/dataplicity-
lomond>`_.

You may also wish to install `wsaccel`, which is a C module containing
optimizations for some websocket operations. Lomond will use it if
available::

    pip install wsaccel

Basic Usage
-----------

To connect to a websocket server, first construct a
`~lomond.websocket.Websocket` object, with a `ws://` or `wss://` URL.
Here is an example::

    from lomond.websocket import WebSocket
    ws = WebSocket('wss://echo.websocket.org')

No socket connection is made by a freshly constructed WebSocket object.
To connect and interact with a websocket server, you must iterate over
the instance. Here's an example::

    for event in ws:
        print(event)

If you run the above code, you should see the events as they are
generated. Here is an example of the output you might get from the above
code::

    Connecting(url='wss://echo.websocket.org')
    Connected(url='wss://echo.websocket.org')
    Ready(<response HTTP/1.1 101 Web Socket Protocol Handshake>, protocol=None, extensions=set([]))

The :class:`~lomond.events.Ready` event indicates a successful
connection to a websocket server. You may now use the
:meth:`~lomond.websocket.WebSocket.send_text` and
:meth:`~lomond.websocket.WebSocket.send_binary` methods to send data to
the server.

When you receive data from the server, a :class:`~lomond.events.Text` or
:class:`~lomond.events.Binary` event will be generated.

Events Basics
-------------

Events exist to inform the application of internal state changes, or
when data is received.

All events are derived from :class:`~lomond.events.Event` and will
contain at lease 2 attributes; `recieved_time` is the epoch time the
event was received, and `name`is the name of the event. Some events have
additional attributes with more information. See the event documentation
for details.

When handling events, you can either check the type with `isinstance` or
by looking at the `name` attribute.

For example, the following two lines are equivalent::

    if isinstance(event, events.Ready)::

or::

    if event.name == "ready"

..node::
    The `isinstance` method is possibly uglier, but has the advantage
    that you are less likely to introduce a bug with a typo in the event
    name.

If an event is generated that you don't wish to handle, then you can
simply ignore it. This is important for backwards compatibility; future
versions of Lomond may introduce new packet types.


Closing the Websocket
---------------------

To close a websocket, call the :meth:`~lomond.websocket.Websocket.close`
method to initiate a *websocket close handshake*. You may call this
method from within the websocket loop, or from another thread.

When a websocket wishes to close it sends a close packet to the server,
which the server will respond to with a close packet of its own. Only
when this echoed close packet is received will the underlaying socket be
closed. This allows both ends of the connection to finish what they are
doing, without losing data.

.. note::
    When you call the `close()` method, you will no longer be able to
    send data, but you may still receive packets from the server until
    the close has completed.

When the websocket has been closed, you will receive a
:class:`~lomond.events.Closed` event, followed by a
    :class:`~lomond.events.Disconnected` event, and the event loop will
        exit.

Polling
-------













