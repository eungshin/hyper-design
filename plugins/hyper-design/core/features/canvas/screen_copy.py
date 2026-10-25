"""Model — 화면 카드 바로 복제 계획(51-6, Figma F19: Ctrl+D = 프레임 복제, 바로 오른쪽에). 데이터 → 데이터 — 파일·네트워크를 쓰지 않는다
(파일 복사·쓰기는 session.apply_edits 의 'clone' 편집). 같은 규칙의 캔버스 쪽 = modules/card-copy.js(화면에 먼저 보일 카드).

plan(screens.json, 원본 id, want=None, title=None, files=()) → {"data": 새 screens.json, "id", "title", "file", "src_file"}
  새 id   = want(캔버스가 고른 것 — 비었으면 아래 규칙) | '<원본>-copy', 쓰였으면 '-copy-2' '-copy-3' … (화면 id · 있는 파일(files = out 기준 경로) 모두 피함)
  새 파일 = 원본 파일과 같은 폴더의 '<새 id>.html'(원본 바이트 그대로 복사 — 화면 안 나가는 링크 그대로)
  제목    = title(앞뒤 빈칸 자름) | 원본 제목(없으면 id) + SUFFIX
  자리    = screens 목록에서 원본 바로 뒤(같은 group — 빌드가 같은 차례로 그 줄에 그린다)
  연결    = 나가는 것(branches) 은 복사본도 그대로 · 들어오는 것(다른 화면 → 원본) 은 원본에만(손대지 않음)
  거절    = CopyError(한국어 이유, reason 'invalid'|'missing') — 앱 카드(개발 서버 주소) · 없는 화면 · 쓰인 id/파일 · 잘못된 id · 긴 제목. 아무것도 바꾸지 않는다.
"""
import copy, posixpath, re

SUFFIX = " 복사"                                     # 옛 복제 메모(canvas_template duplicateCard)와 같은 꼬리
TITLE_MAX = 200
ID_MAX = 120
ID_OK = re.compile(r"^[^/\\:*?\"<>|\s.][^/\\:*?\"<>|\s]*$")   # 파일 이름이 될 수 있는 한 조각(점으로 시작 = 숨은 파일 아님)
DEV_URL = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?/", re.I)   # board_data.is_dev_url 과 같은 앱 카드 판정


class CopyError(Exception):
    def __init__(self, msg, reason="invalid"):
        super().__init__(msg)
        self.reason = reason


def file_of(s):                                      # board_data.index_data 와 같은 기본 경로
    return s.get("file") or "screens/%s.html" % s["id"]


def is_app(f):
    return isinstance(f, str) and bool(DEV_URL.match(f))


def _dest(src_file, nid):
    d = posixpath.dirname(src_file)
    return (d + "/" if d else "") + nid + ".html"


def fresh_id(taken, src, src_file, files=()):
    """'<src>-copy' 부터 화면 id(taken)·파일(files) 이 비는 첫 이름."""
    files = set(files)
    base, n = src + "-copy", 1
    while True:
        nid = base if n == 1 else "%s-%d" % (base, n)
        if nid not in taken and _dest(src_file, nid) not in files:
            return nid
        n += 1


def plan(data, src, want=None, title=None, files=()):
    if not isinstance(data, dict) or not isinstance(data.get("screens"), list):
        raise CopyError("screens.json 을 읽지 못했어요", "missing")
    screens = data["screens"]
    at = next((i for i, s in enumerate(screens) if isinstance(s, dict) and s.get("id") == src), None)
    if at is None:
        raise CopyError("없는 화면이에요: %s — 화면을 새로 불러와 주세요" % (src,), "missing")
    orig = screens[at]
    src_file = file_of(orig)
    if is_app(src_file):
        raise CopyError("앱 카드는 복제할 수 없어요 — 요청(메모)으로만 바꿀 수 있어요")
    taken, files = {s.get("id") for s in screens if isinstance(s, dict)}, set(files)
    if want:
        nid = str(want)
        if len(nid) > ID_MAX or not ID_OK.match(nid):
            raise CopyError("화면 id 로 쓸 수 없는 이름이에요: %s" % nid)
        if "--" in nid and "--" not in src:
            raise CopyError("'--' 가 든 id 는 상태 변형이 돼요: %s" % nid)
        if nid in taken or _dest(src_file, nid) in files:
            raise CopyError("이미 있는 화면 id(또는 파일)예요: %s — 화면을 새로 불러와 주세요" % nid)
    else:
        nid = fresh_id(taken, src, src_file, files)
    t = str(title).strip() if isinstance(title, str) and title.strip() else (orig.get("title") or src) + SUFFIX
    if len(t) > TITLE_MAX:
        raise CopyError("화면 이름이 %d자를 넘어요" % TITLE_MAX)
    new = copy.deepcopy(data)
    entry = copy.deepcopy(orig)
    entry["id"], entry["title"], entry["file"] = nid, t, _dest(src_file, nid)
    new["screens"].insert(at + 1, entry)
    return {"data": new, "id": nid, "title": t, "file": entry["file"], "src_file": src_file}
