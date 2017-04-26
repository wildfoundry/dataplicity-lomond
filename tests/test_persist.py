from lomond.persist import persist
from lomond.websocket import WebSocket
from lomond import events
from threading import Event


def test_persist_with_nonexisting_server():
    websocket = WebSocket('ws://localhost:1234')
    exit_event = Event()
    yielded_events = []
    for event in persist(websocket, exit_event=exit_event):
        yielded_events.append(event)
        exit_event.set()  # break the loop

    # the server doesn't exist, so we expect 3 entries:
    assert len(yielded_events) == 3
    # 0/ Connecting
    assert isinstance(yielded_events[0], events.Connecting)
    # 1/ a ConnectFail - because the server doesn't exist ..
    assert isinstance(yielded_events[1], events.ConnectFail)
    # 2/ and a BackOff which means that we are ready to start a new iteration.
    assert isinstance(yielded_events[2], events.BackOff)
