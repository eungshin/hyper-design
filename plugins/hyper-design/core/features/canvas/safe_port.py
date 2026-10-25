"""Model + edge — 빈 포트(0)로 연 서버가 브라우저가 막는 포트를 받으면 버리고 다시 연다.

Chrome·Edge 는 몇몇 포트를 아예 열지 않는다(ERR_UNSAFE_PORT). Windows 의 동적 포트 범위가 낮게 잡힌 PC 에선
OS 가 그 포트(예: 6566)를 줄 수 있어 캔버스·허브 주소가 브라우저에서 안 열린다. 1024 아래는 OS 가 주지 않으므로 그 위만.
"""

# Chromium net/base/port_util.cc kRestrictedPorts 중 1024 이상
UNSAFE = frozenset({1719, 1720, 1723, 2049, 3659, 4045, 4190, 5060, 5061, 6000, 6566,
                    6665, 6666, 6667, 6668, 6669, 6679, 6697, 10080})
TRIES = 20


def browser_ok(port):
    return port not in UNSAFE


def open_server(cls, host, port, handler):
    """cls((host, port), handler). port 0 = 브라우저가 여는 빈 포트가 나올 때까지(TRIES 번) · 정한 포트는 그대로."""
    srv = cls((host, port), handler)
    tries = 1
    while port == 0 and not browser_ok(srv.server_address[1]) and tries < TRIES:
        srv.server_close()
        srv = cls((host, 0), handler)
        tries += 1
    return srv
