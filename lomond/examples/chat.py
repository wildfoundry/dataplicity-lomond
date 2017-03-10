import logging
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

from threading import Thread

from lomond import events, WebSocket

name = raw_input("your name: ")
ws = WebSocket('ws://ws.willmcgugan.com/chat/')

def run():
    for event in ws:
        if isinstance(event, events.Accepted):
            ws.send_text("<{} connected>".format(name))
        elif isinstance(event, events.Text):
            print event.text

Thread(target=run).start()

while True:
    try:
        ws.send_text("[{}] {}".format(name, raw_input()))
    except KeyboardInterrupt:
        ws.close()
        break
