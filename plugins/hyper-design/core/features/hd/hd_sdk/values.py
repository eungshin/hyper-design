"""Model — 값 객체 Note · Event. 순수(I/O·시계 없음). 규칙은 hd_model(상태·번호·줄) 하나 — 여기서 다시 만들지 않는다.

Note = hd_model.rows 의 줄 객체 하나(hd notes --json 의 notes[] 모양, 키 순서 그대로) + ref·is_open·line.
Event = protocol events.json 의 이벤트 하나 {id:int, type, ts:int ms, project, …나머지}. project.events() 는 아직 없다(task 47-4b).
"""
from dataclasses import dataclass, field

import hd_model


@dataclass(frozen=True)
class Note:
    id: str
    screen: str
    no: int
    status: str
    intent: str
    sent: bool
    edit: object
    scope: str
    target: dict
    text: str
    replies: list

    @classmethod
    def from_row(cls, row):
        return cls(**{k: row.get(k) for k in cls.__dataclass_fields__})

    @classmethod
    def from_state(cls, state, which="open"):
        """상태 파일의 state({notes, note-seq}) → 고른 Note 목록(which = open|sent|all, hd_model.pick)."""
        st = state if isinstance(state, dict) else {}
        notes = st.get("notes") if isinstance(st.get("notes"), list) else []
        return [cls.from_row(r) for r in hd_model.pick(hd_model.rows(notes, st.get("note-seq")), which)]

    @property
    def ref(self):
        """'<screen>#<no>' — hd reply 가 받는 번호."""
        return "%s#%s" % (self.screen, self.no)

    @property
    def is_open(self):
        return self.status in hd_model.OPEN

    def as_dict(self):
        """hd notes --json 의 줄 객체(키 순서 그대로)."""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def line(self):
        """사람용 줄(답은 들여 쓴 줄) — hd_model.format_rows."""
        return hd_model.format_rows([self.as_dict()])


@dataclass(frozen=True)
class Event:
    id: int
    type: str
    ts: int = 0
    project: str = ""
    data: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        """events.json 의 이벤트 → Event. id·type 이 없으면 ValueError(깨진 이벤트는 받는 쪽이 [hd] 한 줄로 건너뛴다)."""
        if not isinstance(d, dict) or type(d.get("id")) is not int or not isinstance(d.get("type"), str):
            raise ValueError("이벤트 모양이 아니에요: %r" % (d,))
        rest = {k: v for k, v in d.items() if k not in ("id", "type", "ts", "project")}
        return cls(d["id"], d["type"], d.get("ts") or 0, d.get("project") or "", rest)
