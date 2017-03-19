from __future__ import print_function
from __future__ import unicode_literals

import logging
import sys
import json

from lomond import WebSocket
from lomond.constants import USER_AGENT

server = 'ws://127.0.0.1:9001'


log = logging.getLogger('wstests')


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
    update_report


def run_ws(url):
    ws = WebSocket(url)
    for event in ws:
        try:
            if event.name == 'text':
                ws.send_text(event.text)
            elif event.name == 'binary':
                ws.send_binary(event.data)
        except:
            log.exception('error running websocket')
            break


def run_test(test_no):
    url = server + '/runCase?case={}&agent={}'.format(test_no, USER_AGENT)
    run_ws(url)


def run_test_cases(case_tuples):
    for case_tuple in case_tuples:
        print("\n[{}]".format(case_tuple))
        url = server + '/runCase?casetuple={}&agent={}'.format(case_tuple, USER_AGENT)
        run_ws(url)
    update_report()


def update_report():
    url = server + "/updateReports?agent=" + USER_AGENT;
    for event in WebSocket(url):
        pass


if __name__ == "__main__":
    print("Run `wstest -m fuzzingserver` to test")
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    test_cases = sys.argv[1:]
    if test_cases:
        run_test_cases(test_cases)
    else:
        run_tests()

