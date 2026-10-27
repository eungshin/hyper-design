"""Client — hd parts: 앱 부품 목록 <out>/parts.json 보기(--check) · 경고 한 줄(hd notes · hd wait). 규칙은 canvas/part_stamp(순수), 읽기·재기는 canvas/parts_file.

parts.json 을 쓰는 곳은 이 모듈 하나(--rebuild — 자물쇠 파일 · 임시 파일 + os.replace). 도우미·캔버스는 읽기만 한다.
부르는 곳: hd.py(cmd_parts · cmd_notes · cmd_wait).
오류 탐지: 깨진 parts.json · 틀린 항목은 '[hd]' 한 줄씩(parts_file) · 고른 부품이 없으면 HdError 한 줄(종료 코드 1).
"""
import pathlib, sys

import hd_client as C  # noqa: F401  — canvas 폴더를 sys.path 에 넣는다(code_probe · part_stamp · parts_file)
import part_stamp as PS  # noqa: E402
import parts_file as PF  # noqa: E402


def check(out, sel=None):
    """부품마다 보고 줄(part_stamp.row). sel = 파일 · 이름(없으면 전부). 고른 것이 없으면 HdError."""
    parts = PF.read(out)
    picked = PS.select(parts, sel)
    if sel not in (None, "", "*") and not picked:
        raise C.HdError("parts.json 에 그 부품이 없어요: %s (있는 것: %s)" % (sel, ", ".join(p["file"] for p in parts) or "없음"))
    return PF.check(out, picked)


def format_rows(rows):
    """사람용 줄: '<file> · 낡음|최신|모름[ · 미커밋 변경 포함] · 빌드 <시각>[ · 지금 미커밋 변경 있음]'."""
    if not rows:
        return "(앱 부품 없음 — out/parts.json)"
    lines = []
    for r in rows:
        bits = [r["file"], r["label"], "빌드 %s" % (r["built_at"] or "기록 없음")]
        if r["dirty_now"]:
            bits.append("지금 " + PS.DIRTY_LABEL)
        lines.append(" · ".join(bits))
    return "\n".join(lines)


def warning(out, target):
    """낡은 부품이 있으면 '[hd] …' 한 줄 | None — parts.json 이 없으면 git 을 부르지 않는다."""
    if not (pathlib.Path(out) / PF.PARTS).is_file():
        return None
    try:
        return PS.warn_line(PF.check(out), target)
    except Exception as e:                            # noqa: BLE001 — 경고 줄 때문에 hd notes · wait 가 실패하지 않는다
        return "[hd] 앱 부품을 보지 못했어요(%s)" % e


def warn(out, target):
    """warning 이 있으면 stderr 로 한 줄(--json 출력을 더럽히지 않게)."""
    line = warning(out, target)
    if line:
        print(line, file=sys.stderr, flush=True)
    return line
