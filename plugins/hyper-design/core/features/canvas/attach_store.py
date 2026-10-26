"""Edge — 첨부 이미지 파일(R22): <out>/.hd-attach/<시각>-<n>.<ext> 에 하나씩 쓰기(임시 파일 + os.replace) · 이름으로 다시 읽기.

상태: 이름 고르기 자물쇠 하나(같은 시각 두 장이 같은 이름을 갖지 않게 — 세션 쓰기 자물쇠는 잡지 않는다: 긴 빌드 중에도 붙이기가 된다).
규칙(종류·한도·이름·rel)은 attach_rules.py(순수). 부르는 곳: session.ProjectSession(images) · router(POST·GET /api/image).
오류 탐지: 폴더·파일이 out 밖으로 풀리면(링크) 400, 쓰기 실패는 임시 파일을 지우고 500 {error} — 반쪽 파일을 남기지 않는다.
"""
import base64, datetime, pathlib, threading

import attach_rules as AR
import out_io


class Attachments:
    """POST /api/image {data, name?} → save · GET /api/image?rel= → read. 돌려주는 경로는 터미널 에이전트가 열 수 있는 절대 경로."""

    def __init__(self, out, now=None):
        self.out = pathlib.Path(out).resolve()
        self.now = now or (lambda: datetime.datetime.now())
        self.lock = threading.Lock()

    @property
    def folder(self):
        return self.out / AR.FOLDER

    def save(self, body):
        got, err = AR.decode(body)
        if err:
            return err
        raw, ext = got
        try:
            self.folder.mkdir(exist_ok=True)
        except OSError as e:
            return 500, {"error": "첨부 폴더를 만들지 못했어요(%s)" % e}
        if not out_io._inside(self.out, self.folder):
            return 400, {"error": "첨부 폴더가 out 밖을 가리켜요(%s) — 그 폴더를 지워 주세요" % AR.FOLDER}
        with self.lock:
            stamp, n = out_io._stamp(self.now()), 1
            while (self.folder / AR.file_name(stamp, n, ext)).exists() or (self.folder / (AR.file_name(stamp, n, ext) + ".tmp")).exists():
                n += 1
            p = self.folder / AR.file_name(stamp, n, ext)
            tmp = p.with_name(p.name + ".tmp")
            try:
                tmp.write_bytes(raw)
                out_io._replace(tmp, p)
            except OSError as e:
                try:
                    tmp.unlink()
                except OSError:                       # 임시 파일이 처음부터 없었다 — 지울 것 없음
                    pass
                return 500, {"error": "이미지를 저장하지 못했어요(%s)" % e}
        return 200, {"path": str(p), "rel": AR.rel_of(p.name), "type": AR.TYPES[ext], "size": len(raw)}

    def read(self, q):
        rel = (q or {}).get("rel", [None])[0]
        name = AR.parse_rel(rel)
        if name is None:
            return 400, {"error": "rel 은 %s/<이름> 이어야 해요" % AR.FOLDER}
        p = self.folder / name
        if not out_io._inside(self.out, p):
            return 400, {"error": "out 밖 경로예요"}
        try:
            raw = p.read_bytes()
        except FileNotFoundError:
            return 404, {"error": "그 첨부 이미지가 없어요 — 지워졌을 수 있어요"}
        except OSError as e:
            return 500, {"error": "첨부 이미지를 읽지 못했어요(%s)" % e}
        return 200, {"rel": AR.rel_of(name), "path": str(p), "type": AR.type_of(name), "data": base64.b64encode(raw).decode("ascii")}
