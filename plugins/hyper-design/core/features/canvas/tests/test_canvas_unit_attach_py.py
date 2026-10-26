"""첨부 이미지(R22) 서버 — attach_rules.py(순수: 앞 바이트로 종류 · 한도 · rel 읽기)는 unit,
Attachments(파일)와 POST·GET /api/image(같은 프로세스 도우미)는 slow."""
import base64, datetime, json, os, subprocess, sys, threading, urllib.error, urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import attach_rules as AR  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
JPG = b"\xff\xd8\xff\xe0" + b"\0" * 16
WEBP = b"RIFF\x10\0\0\0WEBPVP8 " + b"\0" * 8
GIF = b"GIF89a" + b"\0" * 10


def b64(b):
    return base64.b64encode(b).decode("ascii")


def test_sniff_reads_magic_not_name():
    assert [AR.sniff(x) for x in (PNG, JPG, WEBP, GIF)] == ["png", "jpg", "webp", "gif"]
    assert AR.sniff(b"<svg xmlns=") is None and AR.sniff(b"RIFF\0\0\0\0WAVE") is None and AR.sniff(b"") is None and AR.sniff("png") is None


def test_decode_accepts_png_and_data_url_rejects_the_rest():
    (raw, ext), err = AR.decode({"data": b64(PNG), "name": "evil.exe"})
    assert err is None and raw == PNG and ext == "png", "종류는 이름이 아니라 앞 바이트"
    (raw, ext), err = AR.decode({"data": "data:image/png;base64," + b64(PNG)})
    assert raw == PNG and ext == "png"
    assert AR.decode({"data": b64(b"hello world, not an image")})[1][0] == 415
    assert AR.decode({"data": "@@@not base64"})[1][0] == 400
    assert AR.decode({"data": ""})[1][0] == 400 and AR.decode({})[1][0] == 400 and AR.decode([1])[1][0] == 400
    assert AR.decode({"data": "data:image/png,abc"})[1][0] == 400, "base64 가 아닌 data: 주소"


def test_decode_size_cap(monkeypatch):
    monkeypatch.setattr(AR, "MAX_BYTES", 128)
    ok = PNG + b"\0" * (128 - len(PNG))
    assert AR.decode({"data": b64(ok)})[1] is None, "한도까지는 받는다"
    code, res = AR.decode({"data": b64(ok + b"\0")})[1]
    assert code == 413 and "MB" in res["error"]


def test_parse_rel_only_attach_names():
    good = ".hd-attach/20261026-101112-123456-1.png"
    assert AR.parse_rel(good) == "20261026-101112-123456-1.png"
    assert AR.parse_rel(good.replace("/", "\\")) == "20261026-101112-123456-1.png"
    for bad in ("../x.png", ".hd-attach/../../secret.png", "C:/x/.hd-attach/20261026-101112-123456-1.png", "/etc/passwd",
                ".hd-queue/20261026-101112-123456-1.png", ".hd-attach/20261026-101112-123456-1.exe", ".hd-attach/a/b.png", "", None, 3):
        assert AR.parse_rel(bad) is None, bad
    assert AR.file_name("20261026-101112-123456", 2, "jpg") == "20261026-101112-123456-2.jpg"
    assert AR.parse_rel(AR.rel_of(AR.file_name("20261026-101112-123456", 2, "jpg")))


def test_body_cap_fits_a_full_size_image_as_base64():
    full = len(json.dumps({"data": "data:image/png;base64," + "A" * (4 * -(-AR.MAX_BYTES // 3)), "name": "x" * 200}))
    assert full <= AR.BODY_MAX < 2 * AR.MAX_BYTES, "한도 크기 이미지 한 장은 본문 한도 안"


# ---------------------------------------------------------------- 파일 · 서버(slow)
FIXED = datetime.datetime(2026, 10, 26, 10, 11, 12, 123456)


@pytest.mark.slow
def test_save_writes_atomically_and_names_do_not_collide(tmp_path):
    import attach_store
    a = attach_store.Attachments(tmp_path, now=lambda: FIXED)
    c1, r1 = a.save({"data": b64(PNG)})
    c2, r2 = a.save({"data": b64(PNG)})
    c3, r3 = a.save({"data": b64(GIF)})
    assert c1 == c2 == 200
    assert r1["rel"] == ".hd-attach/20261026-101112-123456-1.png" and r2["rel"] == ".hd-attach/20261026-101112-123456-2.png", (r1, r2)
    assert c3 == 200 and r3["rel"].endswith("-1.gif") and r3["type"] == "image/gif", "종류는 앞 바이트"
    p = Path(r1["path"])
    assert p.is_absolute() and p.read_bytes() == PNG and p.parent == tmp_path.resolve() / ".hd-attach"
    assert r1["type"] == "image/png" and r1["size"] == len(PNG)
    assert not list((tmp_path / ".hd-attach").glob("*.tmp")), "임시 파일이 남지 않는다"
    code, got = a.read({"rel": [r1["rel"]]})
    assert code == 200 and base64.b64decode(got["data"]) == PNG and got["type"] == "image/png"
    assert a.read({"rel": [".hd-attach/20261026-101112-123456-9.png"]})[0] == 404
    assert a.read({"rel": ["../screens.json"]})[0] == 400 and a.read({})[0] == 400


@pytest.mark.slow
def test_rejected_or_failed_save_leaves_nothing(tmp_path, monkeypatch):
    import attach_store, out_io
    a = attach_store.Attachments(tmp_path, now=lambda: FIXED)
    assert a.save({"data": b64(b"MZ\x90\0 not an image")})[0] == 415
    assert not (tmp_path / ".hd-attach").exists() or not any((tmp_path / ".hd-attach").iterdir()), "거절이면 아무것도 쓰지 않는다"

    def boom(tmp, p):
        raise PermissionError("locked")
    monkeypatch.setattr(out_io, "_replace", boom)
    code, res = a.save({"data": b64(PNG)})
    assert code == 500 and "저장하지 못했어요" in res["error"], res
    assert not any((tmp_path / ".hd-attach").iterdir()), "쓰기 실패 = 반쪽 파일·임시 파일 없음"


def _link(link, target):
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        return r.returncode == 0
    try:
        os.symlink(target, link)
        return True
    except OSError:
        return False


@pytest.mark.slow
def test_attach_folder_pointing_outside_out_is_refused(tmp_path):
    import attach_store
    out, outside = tmp_path / "out", tmp_path / "elsewhere"
    out.mkdir(); outside.mkdir()
    if not _link(out / ".hd-attach", outside):
        pytest.skip("링크를 만들 수 없음")
    code, res = attach_store.Attachments(out, now=lambda: FIXED).save({"data": b64(PNG)})
    assert code == 400 and "out 밖" in res["error"], res
    assert not any(outside.iterdir()), "out 밖에는 쓰지 않는다"


def _req(url, method="GET", body=None, token=None, raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode("utf-8"))
    r = urllib.request.Request(url, data=data, method=method, headers={"X-HD-Token": token} if token else {})
    try:
        with urllib.request.urlopen(r, timeout=30) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


@pytest.fixture()
def srv(tmp_path):
    import helper
    out = tmp_path / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens.json").write_text(json.dumps({"screens": [{"id": "a", "file": "screens/a.html", "title": "A"}]}), encoding="utf-8")
    (out / "screens" / "a.html").write_text("<main><h1>A</h1></main>", encoding="utf-8")
    (out / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
    s = helper.make_server(out, 0)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    s.base, s.out = s.url.split("/index.html")[0], out
    yield s
    s.shutdown(); s.server_close()


@pytest.mark.slow
def test_api_image_post_get_and_guards(srv):
    api = srv.base + "/api/image"
    assert _req(api, "POST", {"data": b64(PNG)})[0] == 403, "토큰 없이 쓰지 않는다"
    code, res = _req(api, "POST", {"data": b64(PNG), "name": "shot.png"}, srv.token)
    assert code == 200 and res["rel"].startswith(".hd-attach/") and res["type"] == "image/png", res
    p = Path(res["path"])
    assert p.is_absolute() and p.read_bytes() == PNG and p.parent == (srv.out / ".hd-attach").resolve()
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(srv.base + "/" + res["rel"], timeout=10)
    assert e.value.code == 404, "점 폴더는 정적 경로로 내주지 않는다"
    code, got = _req(api + "?rel=" + res["rel"], token=srv.token)
    assert code == 200 and base64.b64decode(got["data"]) == PNG
    assert _req(api + "?rel=../screens.json", token=srv.token)[0] == 400
    assert _req(api, "POST", {"data": b64(b"just text")}, srv.token)[0] == 415
    big = b"\x89PNG\r\n\x1a\n" + b"\0" * (AR.MAX_BYTES + 1)
    code, res = _req(api, "POST", {"data": b64(big)}, srv.token)
    assert code == 413 and "MB" in res["error"], res
    code, res = _req(api, "POST", None, srv.token, raw=b"x" * (AR.BODY_MAX + 1))
    assert code == 413, "본문이 한도를 넘으면 읽기 전에 413"
    assert _req(srv.base + "/api/state", "PUT", None, srv.token, raw=b"x" * (3 * 1024 * 1024))[0] == 413, "다른 주소 본문 한도(2 MB)는 그대로"
    assert len(list((srv.out / ".hd-attach").iterdir())) == 1, "거절된 것은 하나도 쓰지 않았다"
