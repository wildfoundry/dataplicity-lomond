from lomond.constants import WS_KEY, WS_VERSION, USER_AGENT
from uuid import UUID


def test_ws_key():
    _uuid = UUID(hex=WS_KEY.decode())
    # if we are already here it means that UUID constructor did not raise an
    # exception
    assert _uuid.version == 4


def test_ws_version():
    assert WS_VERSION == 13


def test_user_agent():
    assert USER_AGENT.startswith('DataplicityLomond')
