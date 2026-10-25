"""Client 어댑터 — 서버에 말 걸기 하나(HttpTransport)와 hd_client 오류 → HdError 가족 바꾸기(client_errors). 규칙 없음.

Transport 약속(가짜로 바꿔 끼울 수 있게): request(method, path, body=None, timeout=10) → (code, 답 객체). 닿지 않으면 errors.Offline.
HttpTransport 는 hd_client.call(표지의 port·prefix·token) 을 부를 뿐 — HTTP 코드는 한 곳(hd_client)에.
"""
import contextlib

import hd_client as C

from . import errors as E


@contextlib.contextmanager
def client_errors():
    """hd_client 가 던진 오류를 같은 글의 SDK 가족으로(바깥은 hd_sdk.HdError 만 알면 된다)."""
    try:
        yield
    except E.HdError:
        raise
    except C.TimedOut as e:
        raise E.TimedOut(str(e)) from e
    except C.NotFound as e:
        raise E.NotFound(str(e)) from e
    except C.Offline as e:
        raise E.Offline(str(e)) from e
    except C.HdError as e:
        raise E.HdError(str(e)) from e


class HttpTransport:
    """표지(또는 허브 기록) {port, token, prefix?} 하나로 가는 HTTP."""

    def __init__(self, marker):
        self.marker = marker

    def request(self, method, path, body=None, timeout=10):
        with client_errors():
            return C.call(self.marker, path, body, method=method, timeout=timeout)
