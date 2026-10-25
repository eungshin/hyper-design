"""Edge — out 폴더 파일 바탕: out 안인가 · 파일 해시 · 원자적 바꾸기 · JSON 원래 모양대로 쓰기 · 시각 글. 세션 부품이 함께 쓴다.

상태 없음. 규칙(out 안 key)은 hd_projects.inside 하나 — 여기서는 경로를 한 번 풀기만.
부르는 곳: state_store · note_archive · chat_store · busy · ai_undo · send_queue · write_record · screen_edits · board_rows · helper(예전 이름).
오류 탐지: _replace 는 Windows 에서 읽는 중이라 못 바꾸면(PermissionError) 0.02초씩 REPLACE_TRIES 번 다시, 끝내 안 되면 예외를 그대로 올린다.
"""
import datetime, hashlib, json, os, pathlib, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hd"))
import hd_projects  # noqa: E402  — out 안 규칙(inside)은 hd 와 같은 key 하나(#282)


def _inside(out, p):                                 # 규칙은 hd_projects.inside(key: 구분자·끝 '/'·드라이브 대소문자) 하나 — 여기서는 한 번 풀기만
    return hd_projects.inside(str(out), str(pathlib.Path(p).resolve()))



def _sha(p):                                         # 파일 sha256 | None(없음)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None



def _screen_files(data):
    return {s["id"]: s.get("file") or f"screens/{s['id']}.html" for s in data.get("screens", [])}



def _write_json(sj, data, raw):                      # 원래 들여쓰기·끝 줄바꿈을 따라 쓴다
    sj.write_text(json.dumps(data, ensure_ascii=False, indent=2 if '\n  "' in raw else None) + ("\n" if raw.endswith("\n") else ""),
                  encoding="utf-8", newline="")



def _replace(tmp, p):
    for i in range(REPLACE_TRIES):                   # 읽기는 자물쇠 없이 한다(#271) — Windows 는 읽는 중인 파일을 바꾸지 못해 잠깐 기다렸다 다시
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == REPLACE_TRIES - 1:
                raise
            time.sleep(0.02)



REPLACE_TRIES = 25                                   # 0.02초씩 — 읽기 하나는 수 ms



def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")



def _stamp(dt):
    return dt.strftime("%Y%m%d-%H%M%S-%f")
