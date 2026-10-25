"""Edge — AI 되돌리기(48c): 덮개(claim) 동안 그 화면 파일의 쓰기 전 모습을 .hd-history/<stamp>/ 에 남기고, 바뀌면 manifest + 기록 줄 'AI 반영 · <화면>'.

상태: 추적 중인 화면(track) · 기록 줄(log) — 주인 = AiUndo(세션 자물쇠 안에서 불린다). 규칙은 helper_model.ai_*(순수), 여기는 파일만.
부르는 곳: busy.Busy(claim → begin · 지켜보기 → seen · release → end) · session.ProjectSession(GET /api/ai-writes → since).
오류 탐지: 쓰기 전 모습·manifest 를 못 쓰면 [hd] 한 줄 뒤 그 화면은 되돌릴 수 없음으로 둔다(예외를 올리지 않음).
"""
import datetime, json, shutil, sys

from out_io import _inside, _now, _sha, _stamp  # out_io 가 hd 폴더를 sys.path 에 넣는다

import helper_model  # noqa: E402  — ai_begin · ai_seen · ai_end · ai_label · ai_since


class AiUndo:
    """48c AI 되돌리기 — 덮개(claim) 동안 그 화면 파일의 쓰기 전 모습을 .hd-history/<stamp>/ 에 남기고(직접 쓰기와 같은 모양),
    바뀐 것을 보면 manifest(되살리기 기준 = 지금 파일) + 기록 줄 하나 'AI 반영 · <화면>'. 또 바뀌면 같은 줄의 기준만, release 로 끝.
    아무것도 안 바뀌고 끝나면 남긴 모습을 지운다. 규칙은 helper_model.ai_*(순수), 여기는 파일만. 세션 자물쇠 안에서 부른다."""

    def __init__(self, out):
        self.out, self.track, self.log = out, {}, []

    def begin(self, screen, rel):
        if screen in self.track:
            return
        f = self.out / rel
        if not _inside(self.out, f):
            return
        stamp = _stamp(datetime.datetime.now())
        hist = self.out / ".hd-history" / stamp
        try:
            (hist / rel).parent.mkdir(parents=True, exist_ok=True)
            if f.is_file():
                shutil.copy2(f, hist / rel)
        except OSError as e:
            print("[hd] AI 쓰기 전 화면을 남기지 못했어요(%s) — 이 화면의 AI 반영은 되돌릴 수 없어요: %s" % (e, rel), file=sys.stderr, flush=True)
            return
        self.track = helper_model.ai_begin(self.track, screen, stamp, rel, _sha(f), f.is_file())

    def seen(self, screen):
        e = self.track.get(screen)
        if e is None:
            return None
        self.track, act = helper_model.ai_seen(self.track, screen, _sha(self.out / e["rel"]))
        if act is None:
            return None
        e = self.track[screen]
        man = {"files": {e["rel"]: {"before": e["existed"], "after_sha": e["after"]}}, "changed": [screen], "by": "ai"}
        try:
            (self.out / ".hd-history" / e["stamp"] / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as x:
            print("[hd] AI 반영 기록을 쓰지 못했어요(%s): %s" % (x, screen), file=sys.stderr, flush=True)
            return None
        if act == "record":
            self.log.append({"seq": len(self.log) + 1, "stamp": e["stamp"], "screen": screen,
                             "label": helper_model.ai_label(screen, self._title(screen)), "at": _now()})
        return act

    def end(self, screen):
        self.seen(screen)
        self.track, e = helper_model.ai_end(self.track, screen)
        if e is not None and not e["logged"]:          # 안 바뀌었다 — 남긴 모습은 쓸 데가 없다
            shutil.rmtree(self.out / ".hd-history" / e["stamp"], ignore_errors=True)
        return e

    def since(self, since):
        return helper_model.ai_since(self.log, since)

    def row(self, screen):                           # 그 화면을 지금 추적 중인 기록 줄 | None
        e = self.track.get(screen)
        return next((x for x in reversed(self.log) if e and x["stamp"] == e["stamp"]), None)

    def _title(self, screen):
        try:
            return next((x.get("title") for x in json.loads((self.out / "screens.json").read_text(encoding="utf-8")).get("screens", [])
                         if x.get("id") == screen), None)
        except (OSError, ValueError, AttributeError):
            return None
