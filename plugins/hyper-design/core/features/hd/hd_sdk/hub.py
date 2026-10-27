"""Service — Hub: 서버 찾기(<HD_HOME>/home.json) · 떠 있는 캔버스 고르기 · 프로젝트 목록(링크) · 열기 · 새로 · hello(닿기 · 프로젝트에 접속 알리기, 47-5a).

상태 없음 — 매번 hd_client(표지·home.json·projects.json 의 주인)를 읽는다. 고르기 규칙은 hd_model.choose · hd_projects(같은 out = key 하나).
오류는 HdError 가족만(transport.client_errors 가 hd_client 오류를 바꾼다). 홈 서버를 띄우는 일(hd home)은 여기 없다 — home/home_server.
"""
import pathlib

import hd_client as C
import hd_model as M
import hd_projects as P

from . import errors as E
from .project import Project
from .transport import HttpTransport, client_errors


def _same(a, b):
    return P.same(C.abs_out(a), C.abs_out(b))


def _listing(alive):
    return "; ".join("%s (%s)" % (m.get("project"), m.get("out")) for m in alive) or "없음"


class Hub:
    def __init__(self, record=None, transport=None):
        """record = 허브 기록 {port, pid, url, token}(기본 = home.json 에서, 죽은 허브면 None). transport = 허브로 가는 가짜 자리."""
        self._record, self._transport = record, transport

    # ------------------------------------------------------------ 허브 서버
    @property
    def record(self):
        return self._record if self._record is not None else C.hub_record()

    @property
    def running(self):
        return self.record is not None

    @property
    def url(self):
        return (self.record or {}).get("url")

    def _hub(self):
        rec = self.record
        if rec is None and self._transport is None:
            raise E.Offline("홈 서버(허브)가 떠 있지 않아요", next="hd home --no-browser 로 띄우세요")
        return self._transport or HttpTransport({"port": rec["port"], "token": rec["token"]})

    def _hub_call(self, method, path, body=None, timeout=10):
        code, res = self._hub().request(method, path, body, timeout=timeout)
        if code != 200:
            raise E.from_status(code, res, "홈 서버")
        return res

    def hello(self, project=None, **who):
        """인자 없음 = 허브에 닿고 토큰이 맞는지 → {url, port, pid, sessions: 열린 세션 수}(GET /v1/sessions).
        project(이름 | out | None = 떠 있는 하나) 또는 who(id · name · kind · pid · listen · session · lease · beat) 를 주면 = 그 프로젝트에 접속 알리기
        (task 47-5a, Project.hello — 맥박 스레드 포함) → 그 Project(p.me · p.requests() · p.progress() · p.bye())."""
        if project is not None or who:
            p = self.pick(project)
            p.hello(**who)
            return p
        res = self._hub_call("GET", "/v1/sessions")
        rec = self.record or {}
        return {"url": rec.get("url"), "port": rec.get("port"), "pid": rec.get("pid"), "sessions": len(res.get("sessions") or [])}

    def new(self, title=None):
        """허브에 새 프로젝트 POST /api/new {title?} → {name, title, url}(빈 캔버스를 만들고 연다)."""
        return self._hub_call("POST", "/api/new", {} if title is None else {"title": title}, timeout=120)

    # ------------------------------------------------------------ 떠 있는 캔버스
    def canvases(self):
        """살아 있는 서버 세션마다 Project(옛 도우미 + 허브 안 세션)."""
        with client_errors():
            return [Project(m) for m in C.running()]

    def project(self, name=None, out=None, need_helper=False):
        """hd notes·reply 의 고르기 → Project. out 을 주면 그 폴더(떠 있지 않으면 파일만), 아니면 떠 있는 것 중 name(표지 이름·out 경로) 또는 하나뿐인 것.
        못 고르면 NotFound/HdError(떠 있는 것 목록을 붙여). need_helper 면 서버 없는 out 은 Offline(띄우는 명령과 함께)."""
        with client_errors():
            alive = C.running()
        if out:
            o = pathlib.Path(out).resolve()
            if not (o / "screens.json").is_file():
                raise E.NotFound("screens.json 이 있는 out 폴더가 아니에요: %s" % o)
            m = next((m for m in alive if _same(m["out"], o)), None)
        else:
            pool = [m for m in alive if m.get("project") == name or _same(m["out"], name)] if name else alive
            if not pool:
                raise E.NotFound(("'%s' 캔버스가 떠 있지 않아요" % name if name else "떠 있는 캔버스가 없어요") +
                                 " — 떠 있는 것: %s. 파일만 읽으려면 --out PATH" % _listing(alive))
            if len(pool) > 1:
                raise E.HdError("캔버스가 여럿이에요 — 하나를 고르세요(project 또는 --out): %s" % _listing(pool))
            m = pool[0]; o = pathlib.Path(m["out"])
        p = Project(m, out=o)
        if need_helper:
            p._need()
        return p

    def pick(self, ref=None, stale_ok=False):
        """hd stop·attach·wait·claim 의 고르기: 이름(표지 이름 또는 저장한 이름) | out 경로 | None(하나뿐인 것) → Project.
        stale_ok 면 응답 없는 표지도 고른다(hd stop). 규칙 = hd_model.choose."""
        with client_errors():
            keys = set()
            if ref is not None:
                keys.add(P.key(C.abs_out(ref)))
                e = P.find(C.load_projects(), ref)
                if e:
                    keys.add(P.key(C.abs_out(e["out"])))
            m, err = M.choose(C.running(), ref, keys, C.stale() if stale_ok and ref is not None else (), key=lambda o: P.key(C.abs_out(o)))
        if err:
            raise E.NotFound(err)
        return Project(m)

    def target(self, ref=None):
        """hd screens · add 의 고르기 → Project. ref 없음 = 떠 있는 것 하나(hd_model.choose). ref = 표지 이름 · 저장한 이름 · out 경로 —
        떠 있으면 그 세션, 아니면 저장한 링크·out 폴더를 파일만으로(도우미 없음: 읽기 · 화면 넣기는 되고 상태 파일은 쓰지 않는다). 목록에 넣지 않는다."""
        with client_errors():
            alive = C.running()
            if ref is None:
                m, err = M.choose(alive)
                if err:
                    raise E.NotFound(err + " — 이름이나 out 경로를 주세요(hd projects)")
                return Project(m)
            e = P.find(C.load_projects(), ref)
            keys = {P.key(C.abs_out(ref))} | ({P.key(C.abs_out(e["out"]))} if e else set())
            hits = [m for m in alive if m.get("project") == ref or P.key(C.abs_out(m["out"])) in keys]
            if len(hits) > 1:
                raise E.HdError("캔버스가 여럿이에요 — 하나를 고르세요(이름 또는 out 경로): %s" % _listing(hits))
            if hits:
                return Project(hits[0])
            o = e["out"] if e else (C.abs_out(ref) if C.is_out(ref) else None)
            if o is None:
                raise E.NotFound("모르는 캔버스예요: %s — hd projects 로 이름을 보거나 out 경로를 주세요(떠 있는 것: %s)" % (ref, _listing(alive)))
            if not C.is_out(o):
                raise E.NotFound("'%s' 의 out 폴더가 없어요(없음): %s" % (ref, o))
            m = C.live_record(o)                     # 다른 HD_HOME 으로 뜬 도우미도(.hd-helper.json)
        return Project(m, out=o)

    # ------------------------------------------------------------ 프로젝트 목록(링크만)
    def projects(self):
        """저장한 프로젝트 줄 객체 [{name, title, out, state, url, pid, created, last_opened, starred, trashed}]."""
        with client_errors():
            return C.project_rows()

    def open(self, target, agent=None):
        """이름 | out 경로 → (항목, Project, reused). 떠 있으면 그것, 허브가 있으면 그 안에서, 없으면 빌드 후 도우미를 떼어 띄운다. 브라우저는 열지 않음."""
        with client_errors():
            e, m, reused = C.open_project(target, agent)
        return e, Project(m, out=m.get("out") or e["out"]), reused

    def save(self, out=None, name=None):
        """링크 넣기·고치기(복사 없음) → (항목, added, 전 항목 | None). out 기본 = 떠 있는 캔버스 하나."""
        with client_errors():
            if out:
                o = pathlib.Path(C.abs_out(out))
                if not C.is_out(o):
                    raise E.NotFound("screens.json 이 있는 out 폴더가 아니에요: %s" % o)
            else:
                alive = C.running()
                if len(alive) != 1:
                    raise E.HdError(("떠 있는 캔버스가 없어요" if not alive else "캔버스가 여럿이에요(%s)" % _listing(alive)) + " — --out PATH 로 고르세요")
                o = pathlib.Path(C.abs_out(alive[0]["out"]))
            reg = C.load_projects()
            old = P.by_out(reg, str(o))
            try:
                reg, e, added = P.save(reg, str(o), C.now(), name, default_name=C.project_from(o))
            except P.ProjectError as x:
                raise E.Invalid(str(x))
            C.save_projects(reg)
        return e, added, old

    def forget(self, name):
        """링크만 지움(파일은 그대로) → 지운 항목. 없는 이름 = NotFound."""
        with client_errors():
            reg, hit = P.forget(C.load_projects(), name)
            if hit is None:
                raise E.NotFound("저장한 프로젝트에 '%s' 이 없어요 — hd projects" % name)
            C.save_projects(reg)
        return hit
