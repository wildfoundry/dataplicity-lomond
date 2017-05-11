from lomond.parser import Parser
import types


def test_parser_reset_is_a_generator():
    parser = Parser()
    assert isinstance(parser.parse(), types.GeneratorType)
