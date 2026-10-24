"""hd save · projects · open · forget 통합 — HD_HOME 임시, 작은 out 사본, 도우미는 hd open 이 떼어 띄운 진짜 프로세스. 브라우저 없음."""
import json, os, signal, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

HD_PY = hdfix.HD / "hd.py"


def env(home):
    e = hdfix.env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT"):       # 이 테스트의 도우미가 실제 에이전트로 보내지 않게
        e.pop(k, None)
    return e


def hd(home, *args):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=env(home), timeout=60)
    return r.returncode, r.stdout, r.stderr


def hdj(home, *args):
    code, out, err = hd(home, *args, "--json")
    return code, json.loads(out), err


def kill(pid):
    try:
        os.kill(int(pid), signal.SIGTERM)                # Windows: 프로세스 끝냄(떼어 낸 도우미라 Ctrl+Break 를 못 보냄)
    except OSError:
        pass


def test_save_open_reuse_forget(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    (out / "index.html").unlink()                        # open 이 build_ref.py 로 만든다
    home = tmp_path / "home"
    code, o, err = hd(home, "save")
    assert code == 1 and "--out PATH" in err, "떠 있는 캔버스가 없으면 --out 이 필요"
    code, e, err = hdj(home, "save", "--out", str(out), "--name", "My Run")
    assert code == 0 and e["name"] == "my-run" and e["added"] and Path(e["out"]) == out.resolve(), err
    code, rows, _ = hdj(home, "projects")
    assert [(r["name"], r["state"]) for r in rows] == [("my-run", "off")]
    code, text, _ = hd(home, "projects")
    assert text.startswith("my-run · ") and " · 꺼짐 · " in text

    pid = None
    try:
        t0 = time.time()
        code, a, err = hdj(home, "open", "my-run", "--no-open")
        assert code == 0 and not a["reused"] and a["url"].startswith("http://127.0.0.1:"), err
        pid = a["pid"]
        assert time.time() - t0 < 30 and (out / "index.html").is_file(), "빌드 후 띄움"
        assert list((home / "active").glob("*.json")), "표지가 생김"
        assert (out / ".hd-helper.log").is_file() and not (out.parent / "helper.log").exists(), "로그는 out 안(#281)"
        code, b, err = hdj(home, "open", str(out), "--no-open")
        assert code == 0 and b["reused"] and b["pid"] == pid and b["url"] == a["url"], "두 번째 open 은 같은 도우미"
        code, rows, _ = hdj(home, "projects")
        assert rows[0]["state"] == "running" and rows[0]["url"] == a["url"] and rows[0]["last_opened"]
        reg = json.loads((home / "projects.json").read_text(encoding="utf-8"))
        assert len(reg["projects"]) == 1, "도우미가 시작 때 같은 out 을 다시 넣지 않는다"
    finally:
        if pid:
            kill(pid)

    code, gone, err = hdj(home, "forget", "my-run")
    assert code == 0 and gone["name"] == "my-run", err
    assert json.loads((home / "projects.json").read_text(encoding="utf-8"))["projects"] == []
    assert (out / "screens.json").is_file() and (out / ".hd-canvas.json").is_file(), "링크만 지우고 파일은 그대로"
    code, o, err = hd(home, "forget", "my-run")
    assert code == 1 and "없어요" in err


def test_helper_registers_its_out_and_missing_out_shows(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    try:
        code, rows, err = hdj(home, "projects")
        assert code == 0 and [(r["name"], r["state"], r["url"]) for r in rows] == [("proj-a", "running", url)], err
        code, e, err = hdj(home, "save")
        assert code == 0 and e["name"] == "proj-a" and not e["added"], "기본 out = 떠 있는 하나"
    finally:
        hdfix.stop_helper(p)
    (out / "screens.json").rename(out / "screens.json.x")
    code, rows, _ = hdj(home, "projects")
    assert rows[0]["state"] == "missing", "없어진 out 은 '없음'으로 남는다(지우지 않음)"
    code, o, err = hd(home, "open", "proj-a", "--no-open")
    assert code == 1 and "없음" in err and "hd forget proj-a" in err


def test_broken_registry_is_set_aside(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    (home / "projects.json").write_text("{nope", encoding="utf-8")
    code, rows, err = hdj(home, "projects")
    assert code == 0 and rows == [] and "[hd]" in err
    assert not (home / "projects.json").exists() and list(home.glob("projects.json.corrupt-*"))
