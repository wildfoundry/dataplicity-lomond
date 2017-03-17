from __future__ import print_function
from __future__ import unicode_literals

import json

from lomond import WebSocket
from lomond.constants import USER_AGENT

server = 'ws://127.0.0.1:9001'


def get_test_count():
    ws = WebSocket(server + '/getCaseCount')
    for event in ws:
        if event.name == 'text':
            case_count = json.loads(event.text)
    return case_count

def run_tests():
    test_count = get_test_count()
    print("Will run {} cases...".format(test_count))

    for test_no in range(1, test_count + 1):
        print("[{} of {}]".format(test_no, test_count))
        run_test(test_no)

def run_test(test_no):
    url = server + '/runCase?case={}&agent={}'.format(test_no, USER_AGENT)
    print(url)
    ws = WebSocket(url)
    for event in ws:
        print(event)
        if event.name == 'text':
            ws.send_text(event.text)
        elif event.name == 'binary':
            ws.send_binary(event.data)


if __name__ == "__main__":
    print("Run `wstest -m fuzzingserver` to test")
    run_tests()