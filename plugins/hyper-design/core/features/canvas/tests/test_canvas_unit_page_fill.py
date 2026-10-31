"""보드 전환 1단계 P1b — 줄 때 끼우는 데이터: 공용 셸 뼈대(shell_store.get(도장)["skeleton"]) + 지금 데이터(Builder.data) + 셸 참조(공용 주소) + inject.
끼우기 규칙(page_fill — 순수) · build_index 와 같은 hd-data 이스케이프 · 세션 page() 가 뼈대가 있으면 빌드 프로세스 0번 · 없으면 예전 길. 하위 프로세스 없음(가짜 빌드·가짜 셸)."""
import json, pathlib, subprocess, sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "hd" / "tests"))
import board_data as BD  # noqa: E402
import build_canvas as BC  # noqa: E402
import code_stamp as CS  # noqa: E402
import hdfix  # noqa: E402
import page_fill as PF  # noqa: E402
import session as S  # noqa: E402

STAMP = "g:cccccccccccccccc"
REFS = {"js": "/v1/shell/%s/hd-shell.js" % STAMP, "css": "/v1/shell/%s/hd-shell.css" % STAMP}


def skeleton(stamp=STAMP):
    """P1a 의 --shell 뼈대와 같은 모양(가정 — page_fill 머리 주석): 템플릿에서 본 스크립트만 뺀 것 + 코드 도장 meta, 자리 네 개는 빈 채로."""
    tpl, _main = BC.split_shell(BC.TEMPLATE.read_text(encoding="utf-8"))
    return CS.stamp_page(tpl, stamp)


DATA = {"rows": [{"screens": [{"file": "screens/a.html", "title": "<b>A</b> & \"B\""}]}], "arrows": [],
        "note": "</script><script>alert(1)</script> <!-- x -->"}


# ---------------------------------------------------------------- 끼우기 규칙(순수)
def test_data_json_escapes_script_end_and_comment_open_and_round_trips():
    blob = PF.data_json(DATA)
    assert "</" not in blob and "<!--" not in blob, blob
    assert json.loads(blob) == DATA, "이스케이프해도 JSON 은 같은 값"


def test_page_html_fills_data_links_shell_refs_stamp_and_inject():
    html = PF.page_html(skeleton(), DATA, REFS, inject="<script>window.__hdHelper=true;</script>", inputs="d:aaaaaaaaaaaaaaaa")
    assert PF.DATA_SLOT not in html and '<script id="hd-data" type="application/json">%s</script>' % PF.data_json(DATA) in html
    assert '<li><a href="screens/a.html">&lt;b&gt;A&lt;/b&gt; &amp; &quot;B&quot;</a></li>' in html, "noscript 링크 — 글은 이스케이프"
    assert '<li><a href="foundation.html">Foundation</a></li><li><a href="components.html">Components</a></li>' in html
    assert '<link rel="stylesheet" href="%s">' % REFS["css"] in html and '<script src="%s"></script>' % REFS["js"] in html
    assert PF.CSS_SLOT not in html and PF.JS_SLOT not in html
    assert html.index('href="%s"' % REFS["css"]) < html.index("<script id=\"hd-data\"") < html.index('src="%s"' % REFS["js"]), "셸 스크립트는 hd-data 뒤"
    assert CS.page_stamp(html) == STAMP and CS.page_inputs(html) == "d:aaaaaaaaaaaaaaaa"
    assert html.startswith(html[:html.index("<head>")] + "<head><script>window.__hdHelper=true;</script>"), "inject 는 <head> 바로 뒤"
    assert "alert(1)</script>" not in html


def test_page_html_escapes_refs_in_attributes():
    html = PF.page_html(skeleton(), DATA, {"js": '/x".js', "css": "/y.css?a=1&b=2"})
    assert 'src="/x&quot;.js"' in html and 'href="/y.css?a=1&amp;b=2"' in html


@pytest.mark.parametrize("slot", ["DATA_SLOT", "LINKS_SLOT", "CSS_SLOT", "JS_SLOT"])
def test_page_html_refuses_a_skeleton_without_a_slot(slot):
    bad = skeleton().replace(getattr(PF, slot), "")
    with pytest.raises(PF.SlotMissing) as e:
        PF.page_html(bad, DATA, REFS)
    assert getattr(PF, slot) in str(e.value)


def test_page_html_refuses_missing_head_and_bad_refs():
    with pytest.raises(PF.SlotMissing):
        PF.page_html(skeleton().replace("<head>", "<head x>"), DATA, REFS, inject="<script></script>")
    with pytest.raises(PF.SlotMissing):
        PF.page_html(skeleton(), DATA, {"js": REFS["js"]})


def test_build_index_uses_the_same_data_rule(tmp_path, monkeypatch):
    out = hdfix.make_out(tmp_path)
    monkeypatch.setenv("HD_CODE_STAMP", STAMP)
    m = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    m["screens"][0]["title"] = "</script><!-- 홈"
    (out / "screens.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    BC.build_index(out, m)
    disk = (out / "index.html").read_text(encoding="utf-8")
    data = BD.index_data(out, m)
    served = PF.page_html(skeleton(), data, REFS, inputs=BD.input_stamp(out))
    pick = lambda h, a, b: h[h.index(a):h.index(b, h.index(a))]
    assert pick(disk, '<script id="hd-data"', "</script>") == pick(served, '<script id="hd-data"', "</script>"), "hd-data 는 build_index 와 같은 글"
    assert pick(disk, '<noscript id="hd-links">', "</noscript>") == pick(served, '<noscript id="hd-links">', "</noscript>")
    assert CS.page_inputs(disk) == CS.page_inputs(served) and CS.page_stamp(disk) == CS.page_stamp(served)


# ---------------------------------------------------------------- 세션 page() — 뼈대가 있으면 빌드 없이
def _counting_build(calls):
    def build(o):
        calls.append(1)
        (o / "index.html").write_text(CS.stamp_page(CS.stamp_inputs("<html><head></head><body>disk %d</body></html>" % len(calls),
                                                                    BD.input_stamp(o)), STAMP), encoding="utf-8")
        return subprocess.CompletedProcess([], 0, "", "")
    return build


def _session(out, calls, shell, code=lambda: STAMP):
    asked = []

    def provider(stamp):
        asked.append(stamp)
        return shell(stamp) if callable(shell) else shell
    sess = S.ProjectSession(out, build=_counting_build(calls), code=code, shell=provider)
    return sess, asked


def test_page_after_a_screen_edit_serves_new_data_without_any_build(tmp_path):
    out = hdfix.make_out(tmp_path)
    calls = []
    sess, asked = _session(out, calls, {"dir": tmp_path, "skeleton": skeleton(), **REFS})
    disk = (out / "index.html").read_bytes()
    code, r = sess.history.apply([{"id": "e1", "screen": "home", "edit": "title", "value": "새 홈 이름"}])
    assert code == 200 and r["applied"] == ["e1"], r
    page = sess.page().decode("utf-8")
    assert calls == [], "빌드 프로세스 0번(코드 도장·데이터 도장 다시 빌드 둘 다 안 함)"
    assert asked == [STAMP], "지금 코드 도장으로 셸을 묻는다"
    assert "새 홈 이름" in page and REFS["js"] in page and CS.page_stamp(page) == STAMP
    assert CS.page_inputs(page) == BD.input_stamp(out), "데이터 도장 = 지금 out"
    assert "window.__hdHelper=true" in page and "__hdState" in page, "inject 는 그대로"
    assert (out / "index.html").read_bytes() == disk, "디스크 index.html 은 읽지도 굽지도 않는다"


def test_page_without_shell_takes_the_old_path(tmp_path):
    out = hdfix.make_out(tmp_path)
    calls = []
    sess, asked = _session(out, calls, None)
    page = sess.page().decode("utf-8")
    assert asked == [STAMP] and calls == [1] and "disk 1" in page, "셸이 없으면 예전 길(옛 도장 페이지 다시 빌드 + 디스크)"
    plain = S.ProjectSession(out, build=_counting_build(calls), code=lambda: STAMP)
    assert plain.shell is None and "disk" in plain.page().decode("utf-8"), "shell 을 안 넘기면 지금과 같다"


def test_page_falls_back_when_shell_or_data_fails(tmp_path, capsys):
    out = hdfix.make_out(tmp_path)
    calls = []
    sess, _ = _session(out, calls, lambda s: (_ for _ in ()).throw(OSError("셸 폴더 없음")))
    assert "disk" in sess.page().decode("utf-8") and calls == [1]
    assert "[hd]" in capsys.readouterr().err
    sess2, _ = _session(out, calls, {"dir": tmp_path, "skeleton": "<html><head></head><body>자리 없음</body></html>", **REFS})
    assert "disk" in sess2.page().decode("utf-8"), "자리 없는 뼈대 → 예전 길"
    assert "[hd]" in capsys.readouterr().err
    (out / "screens.json").write_text("{깨짐", encoding="utf-8")
    sess3, _ = _session(out, calls, {"dir": tmp_path, "skeleton": skeleton(), **REFS})
    assert "disk" in sess3.page().decode("utf-8"), "데이터 계산 실패 → 예전 길(디스크 index.html)"
    assert "[hd]" in capsys.readouterr().err


def test_page_without_code_stamp_takes_the_old_path(tmp_path):
    out = hdfix.make_out(tmp_path)
    calls = []
    sess, asked = _session(out, calls, {"dir": tmp_path, "skeleton": skeleton(), **REFS}, code=None)
    assert b"canvas" in sess.page() and asked == [], "지금 도장을 모르면 셸을 묻지 않는다"
