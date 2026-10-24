"""Client — 바탕 화면 바로 가기 `Hyper Design.lnk`(→ pythonw.exe "<hd.py>" home) 와 그 아이콘 <HD_HOME>/hd.ico.

- 바탕 화면 = [Environment]::GetFolderPath('Desktop')(테스트는 임시 폴더를 넘긴다)
- 대상 = sys.executable 옆 pythonw.exe(없으면 python.exe) · 인자 "<hd.py>" home · 작업 폴더 HD_HOME · 아이콘 hd.ico
- 아이콘 = PNG 하나를 담은 ICO(256px, 캔버스 머리의 "hd" 배지: 짙은 둥근 네모 + 흰 hd). 만들지 못하면 아이콘 없이 — 바로 가기는 실패하지 않는다
- .lnk 쓰기는 PowerShell WScript.Shell(표준 라이브러리만 — pywin32 없음)
"""
import base64, os, pathlib, struct, subprocess, sys, zlib

HERE = pathlib.Path(__file__).resolve().parent
HD_PY = HERE.parent / "hd" / "hd.py"
NAME = "Hyper Design.lnk"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BG, FG = (0x2B, 0x2B, 0x29), (0xFF, 0xFF, 0xFF)


class ShortcutError(Exception):
    """사용자에게 그대로 보일 한 줄."""


def _ps():
    return str(pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")


def _run_ps(script):
    enc = base64.b64encode(("[Console]::OutputEncoding = [Text.Encoding]::UTF8\n" + script).encode("utf-16-le")).decode("ascii")
    return subprocess.run([_ps(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc], capture_output=True,
                          encoding="utf-8", errors="replace", creationflags=NO_WINDOW)


def desktop():
    """사용자 바탕 화면 폴더(OneDrive 로 옮긴 것도)."""
    r = _run_ps("Write-Output ([Environment]::GetFolderPath('Desktop'))")
    p = (r.stdout or "").strip()
    if r.returncode != 0 or not p:
        raise ShortcutError("바탕 화면 폴더를 찾지 못했어요: %s" % (r.stderr or "").strip())
    return pathlib.Path(p)


def pythonw():
    exe = pathlib.Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return w if w.is_file() else exe


# ---------------------------------------------------------------- 아이콘 (PNG 를 담은 ICO, 표준 라이브러리만)
def _cover(x, y, s):
    """(x, y) 가 0..1 좌표에서 배지 위 어디인가 → 'fg' | 'bg' | None(바깥). 둥근 네모 + 'h' 'd' 획."""
    r = 0.22
    cx, cy = min(max(x, r), 1 - r), min(max(y, r), 1 - r)
    if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
        return None
    x, y = 0.5 + (x - 0.5) / 0.72, 0.5 + (y - 0.5) / 0.72  # 글자는 네모 안 72% 에(가장자리 여백)
    w = 0.058                                             # 획 굵기(반)
    # h: 세로 막대 + 둥근 어깨 + 오른 다리
    if 0.18 - w <= x <= 0.18 + w and 0.24 <= y <= 0.76:
        return "fg"
    hx, hy, hr = 0.31, 0.53, 0.13
    d = ((x - hx) ** 2 + (y - hy) ** 2) ** 0.5
    if y <= hy and abs(d - hr) <= w:
        return "fg"
    if 0.44 - w <= x <= 0.44 + w and hy <= y <= 0.76:
        return "fg"
    # d: 둥근 고리 + 오른 막대
    dx, dy, dr = 0.69, 0.61, 0.13
    if abs(((x - dx) ** 2 + (y - dy) ** 2) ** 0.5 - dr) <= w:
        return "fg"
    if 0.82 - w <= x <= 0.82 + w and 0.24 <= y <= 0.76:
        return "fg"
    return "bg"


def badge_png(size=256, ss=3):
    """배지 PNG 바이트(RGBA, ss×ss 표본으로 가장자리 부드럽게)."""
    rows = []
    n = ss * ss
    for py in range(size):
        row = bytearray(b"\x00")
        for px in range(size):
            f = b = 0
            for sy in range(ss):
                for sx in range(ss):
                    c = _cover((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size, size)
                    if c == "fg":
                        f += 1
                    elif c == "bg":
                        b += 1
            a = f + b
            if a == 0:
                row += b"\x00\x00\x00\x00"
                continue
            mix = [round((BG[i] * b + FG[i] * f) / a) for i in range(3)]
            row += bytes(mix + [round(255 * a / n)])
        rows.append(bytes(row))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def ico_bytes(png, size=256):
    """PNG 하나를 담은 ICO(Vista 이후 그대로 읽는다). 256 은 머리글에 0 으로 적는다."""
    s = 0 if size >= 256 else size
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(png), 6 + 16) + png


def make_icon(path):
    """<HD_HOME>/hd.ico 를 만든다(있으면 그대로) → 경로 | None(실패 — [hd] 한 줄, 바로 가기는 아이콘 없이)."""
    p = pathlib.Path(path)
    if p.is_file() and p.stat().st_size > 0:
        return p
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_bytes(ico_bytes(badge_png()))
        os.replace(tmp, p)
        return p
    except OSError as e:
        print("[hd] 아이콘을 만들지 못했어요(%s) — 아이콘 없이 만들어요" % e, file=sys.stderr, flush=True)
        return None


# ---------------------------------------------------------------- 바로 가기
def _q(s):
    return "'" + str(s).replace("'", "''") + "'"


def write_shortcut(home, desk=None):
    """<바탕 화면>/Hyper Design.lnk 를 쓴다(덮어씀) → .lnk 경로. Windows 가 아니거나 쓰지 못하면 ShortcutError."""
    if sys.platform != "win32":
        raise ShortcutError("바탕 화면 바로 가기는 Windows 에서만 만들어요")
    home = pathlib.Path(home)
    home.mkdir(parents=True, exist_ok=True)
    desk = pathlib.Path(desk) if desk else desktop()
    if not desk.is_dir():
        raise ShortcutError("바탕 화면 폴더가 없어요: %s" % desk)
    lnk = desk / NAME
    icon = make_icon(home / "hd.ico")
    script = "\n".join([
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(%s)" % _q(lnk),
        "$s.TargetPath = %s" % _q(pythonw()),
        "$s.Arguments = %s" % _q('"%s" home' % HD_PY),
        "$s.WorkingDirectory = %s" % _q(home),
        "$s.Description = %s" % _q("Hyper Design — 모든 캔버스"),
    ] + (["$s.IconLocation = %s" % _q("%s,0" % icon)] if icon else []) + ["$s.Save()"])
    r = _run_ps(script)
    if r.returncode != 0 or not lnk.is_file():
        raise ShortcutError("바로 가기를 쓰지 못했어요(%d): %s" % (r.returncode, " / ".join((r.stderr or "").strip().splitlines()[-2:])))
    return lnk


def read_shortcut(lnk):
    """.lnk → {target, args, workdir, icon}(테스트·확인용)."""
    r = _run_ps("$s = (New-Object -ComObject WScript.Shell).CreateShortcut(%s); "
                "Write-Output $s.TargetPath; Write-Output $s.Arguments; Write-Output $s.WorkingDirectory; Write-Output $s.IconLocation" % _q(lnk))
    if r.returncode != 0:
        raise ShortcutError("바로 가기를 읽지 못했어요: %s" % (r.stderr or "").strip())
    lines = (r.stdout or "").splitlines() + [""] * 4
    return {"target": lines[0], "args": lines[1], "workdir": lines[2], "icon": lines[3]}
