"""safe_port — 빈 포트(0)로 열 때 브라우저가 막는 포트(Chrome ERR_UNSAFE_PORT, 예: 6566)는 버리고 다시 연다."""
import pathlib, sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import safe_port  # noqa: E402

pytestmark = pytest.mark.unit


class Fake:
    """열 때마다 다음 포트를 받는 가짜 서버(0 이면 given 에서 차례로)."""
    given, closed = [], []

    def __init__(self, addr, handler):
        port = addr[1] or Fake.given.pop(0)
        self.server_address = (addr[0], port)

    def server_close(self):
        Fake.closed.append(self.server_address[1])


def test_browser_blocked_ports_are_unsafe():
    assert not safe_port.browser_ok(6566) and not safe_port.browser_ok(10080) and not safe_port.browser_ok(6667)
    assert safe_port.browser_ok(12279) and safe_port.browser_ok(54321)


def test_port_zero_retries_until_the_browser_can_open_it():
    Fake.given, Fake.closed = [6566, 5060, 54321], []
    srv = safe_port.open_server(Fake, "127.0.0.1", 0, None)
    assert srv.server_address[1] == 54321 and Fake.closed == [6566, 5060]


def test_asked_port_is_kept_as_is():
    Fake.given, Fake.closed = [], []
    assert safe_port.open_server(Fake, "127.0.0.1", 6566, None).server_address[1] == 6566
