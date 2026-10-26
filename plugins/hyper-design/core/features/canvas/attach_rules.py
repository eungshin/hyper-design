"""Model — 첨부 이미지(R22) 규칙: 종류는 이름이 아니라 앞 바이트(magic)로 · 크기 한도 · base64 풀기 · 파일 이름 · out 기준 경로(rel) 읽기. I/O 없음.

부르는 곳: attach_store.Attachments(POST·GET /api/image) · router(BODY_MAX — 이 주소만 본문 한도가 크다).
파일 자리: <out>/.hd-attach/<시각>-<n>.<ext>(시각 = out_io._stamp). 점 폴더라 정적 경로로는 내주지 않고 GET /api/image 로만(토큰).
"""
import base64, binascii, re

FOLDER = ".hd-attach"
MAX_BYTES = 10 * 1024 * 1024                         # 이미지 한 장 한도(풀린 바이트)
BODY_MAX = MAX_BYTES * 4 // 3 + 64 * 1024            # POST 본문 한도 — base64(4/3) + JSON 머리. 넘으면 라우터가 413
TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
NAME = re.compile(r"^\d{8}-\d{6}-\d{6}-\d{1,4}\.(png|jpg|webp|gif)$")
LINE = "첨부 이미지: "                                # 요청 글 한 줄 머리(캔버스 modules/attach.js 와 같은 말) — 뒤는 절대 경로 끝까지


def sniff(b):
    """앞 바이트 → 확장자 | None(PNG·JPEG·WebP·GIF 만)."""
    if not isinstance(b, (bytes, bytearray)):
        return None
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


def too_big(n):
    return "이미지가 너무 커요(%.1f MB) — %d MB 까지 붙일 수 있어요" % (n / 1024 / 1024, MAX_BYTES // 1024 // 1024)


def decode(body):
    """POST 본문 {data: base64 | 'data:…;base64,…', name?} → (bytes, ext) | 오류 (code, {error}).
    400 = 모양·base64 틀림 · 413 = 한도 넘음 · 415 = 이미지 종류가 아님(앞 바이트)."""
    if not isinstance(body, dict):
        return None, (400, {"error": "JSON 객체가 아니에요({data} 모양으로 보내 주세요)"})
    data = body.get("data")
    if not isinstance(data, str) or not data.strip():
        return None, (400, {"error": "data(base64 이미지)가 없어요"})
    data = data.strip()
    if data.startswith("data:"):
        head, _, data = data.partition(",")
        if ";base64" not in head:
            return None, (400, {"error": "data: 주소는 base64 여야 해요"})
    if len(data) * 3 // 4 > MAX_BYTES + 3:
        return None, (413, {"error": too_big(len(data) * 3 // 4)})
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return None, (400, {"error": "base64 가 아니에요"})
    if len(raw) > MAX_BYTES:
        return None, (413, {"error": too_big(len(raw))})
    if not raw:
        return None, (400, {"error": "빈 이미지예요"})
    ext = sniff(raw)
    if ext is None:
        return None, (415, {"error": "PNG·JPEG·WebP·GIF 이미지만 붙일 수 있어요"})
    return (raw, ext), None


def file_name(stamp, n, ext):
    return "%s-%d.%s" % (stamp, n, ext)


def rel_of(name):
    return FOLDER + "/" + name


def parse_rel(rel):
    """GET ?rel= → 파일 이름 | None. '.hd-attach/<이름>' 만(구분자 / 또는 \\), 이름은 이 규칙이 만든 모양뿐 — '..'·절대 경로·다른 폴더는 None."""
    if not isinstance(rel, str):
        return None
    parts = rel.replace("\\", "/").split("/")
    if len(parts) != 2 or parts[0] != FOLDER or not NAME.match(parts[1]):
        return None
    return parts[1]


def type_of(name):
    return TYPES.get(name.rsplit(".", 1)[-1])
