"""Model — HdError 가족: 한국어 한 줄(message) + 다음 행동(next). 순수(I/O·시계 없음).

가족: Offline(닿지 않음) · NotFound(없음 404) · Conflict(rev 어긋남 409) · TooLarge(2 MB 넘음 413) · Unauthorized(토큰·주소 403/401) ·
Invalid(규칙 어긋남 400) · TimedOut(기다림 끝, 종료 코드 2) · NotYet(아직 없는 기능 — events, task 47-4b).
str(e) = message 그대로(CLI 가 'hd: ' 를 붙여 찍는다). next 는 따로 두고, 보여 줄 때만 line() 이 같은 줄에 ' — 다음: …' 로 붙인다.
"""


class HdError(Exception):
    """사용자에게 보일 한 줄 오류. code = CLI 종료 코드(기본 1)."""
    code = 1
    default_next = None

    def __init__(self, message, next=None):
        super().__init__(message)
        self.message = message
        self.next = next if next is not None else self.default_next

    @property
    def kind(self):
        return type(self).__name__

    def line(self):
        """한 줄: 메시지 + (다음 행동이 있고 메시지에 아직 없으면) ' — 다음: …'."""
        if self.next and self.next not in self.message:
            return "%s — 다음: %s" % (self.message, self.next)
        return self.message

    def as_dict(self):
        d = {"error": self.message, "kind": self.kind}
        if self.next:
            d["next"] = self.next
        return d


class Offline(HdError):
    default_next = "hd ls 로 떠 있는지 보고, 없으면 hd open <이름> 으로 띄우세요"


class NotFound(HdError):
    default_next = None                                # 메시지마다 다음 행동이 다르다(hd notes --all · hd projects …) — 만드는 쪽이 준다


class Conflict(HdError):
    default_next = "최신 상태를 다시 읽고(hd notes) 다시 하세요"


class TooLarge(HdError):
    default_next = "완료 메모를 보관으로 옮기세요(캔버스 메모 패널)"


class Unauthorized(HdError):
    default_next = "서버가 다시 떠 토큰이 바뀌었어요 — hd ls 로 다시 찾으세요"


class Invalid(HdError):
    pass


class TimedOut(HdError):
    code = 2


class NotYet(HdError):
    default_next = "지금은 hd wait(2초 확인)를 쓰세요"


BY_STATUS = {401: Unauthorized, 403: Unauthorized, 404: NotFound, 409: Conflict, 413: TooLarge, 400: Invalid}


def from_status(code, body, who="도우미"):
    """서버가 거절한 답(code, {error|errors}) → 가족 중 하나. 메시지 = '<who>가 거절했어요(code): …'(지금 CLI 글 그대로)."""
    body = body if isinstance(body, dict) else {}
    why = "\n  ".join(body.get("errors") or [body.get("error", "")])
    return BY_STATUS.get(code, HdError)("%s가 거절했어요(%d): %s" % (who, code, why))
