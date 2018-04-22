import types

import pytest

from lomond.parser import ParseError, Parser


def test_parser_reset_is_a_generator():
    parser = Parser()
    assert isinstance(parser.parse(), types.GeneratorType)


def test_max_bytes():
    class TestParser(Parser):
        def parse(self):
            data = yield self.read_until(b'\r\n\r\n', max_bytes=100)
            print("***", data)
            yield data

    test_data = [b'foo'] * 100
    test_parser = TestParser()
    with pytest.raises(ParseError):
        for data in test_data:
            for _data in test_parser.feed(data):
                print(_data)
