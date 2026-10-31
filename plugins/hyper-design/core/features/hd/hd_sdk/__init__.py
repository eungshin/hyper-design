"""hd_sdk — Hyper Design SDK(표준 라이브러리만). 터미널 에이전트가 떠 있는 캔버스 서버에 말을 거는 객체들. 계약 = contract.md.

    from hd_sdk import Hub, HdError
    hub = Hub()
    p = hub.pick()                       # 떠 있는 캔버스 하나(여럿이면 hub.pick("이름"))
    for n in p.notes():                  # 보냈고 끝나지 않은 메모(Note)
        p.claim(n.screen, by="me")
        ...                              # 화면 파일 고치기
        p.reply(n.ref, {"kind": "반영됨", "what": "…", "screens": [n.screen], "captured": False})

층: errors·values(Model, 순수) → transport(Client 어댑터: hd_client) → project·hub(Service) → text(View). hd CLI(hd.py)는 이 위의 얇은 껍데기.
"""
from .errors import (HdError, Offline, NotFound, Conflict, TooLarge, Unauthorized, Invalid, TimedOut, NotYet,  # noqa: F401
                     from_status)
from .values import Note, Event  # noqa: F401
from .transport import HttpTransport, client_errors  # noqa: F401
from .project import Project, check_claim, check_agent  # noqa: F401
from .hub import Hub  # noqa: F401
from . import text  # noqa: F401
from hd_model import AGENT_KINDS, parse_ref, reply_warns  # noqa: F401,E402  — 답을 보내기 전 막지 않는 경고(R35) · 에이전트가 쓸 수 있는 답 종류(반영됨·일부·대체됨·답변·질문) · '<screen>#<no>' | 메모 id 풀기
from hd_place import format_rows as place_text, pos_label as place_pos, size_label as place_size, split_add_args  # noqa: F401,E402  — hd screens · add 의 사람용 줄 · add 위치 인자 풀이(옛 모양)
