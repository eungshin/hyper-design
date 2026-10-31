"""Model — 부품 쓰는 화면 지도(R58): 어떤 화면이 어떤 부품(견본 key)을 쓰나 + components.html 에 넣을 칩·목록 글. 파일·네트워크를 쓰지 않는다.

"쓴다" = 그 화면 파일 안 어떤 요소의 class 에 견본 key 가 있다(build_canvas.used_classes 거르기와 같은 뜻).
classes(html) → set · spec_keys(specimens html) → [key](문서 차례) · usage(keys, [(id, classes)]) → {key: [id …]}(화면 차례, 빈 key·배지 빠짐) ·
mark_section(여는 태그, key, ids) → data-used·id·머리 칩을 단 여는 태그 · index_html([(key, title, n)]) → 맨 위 얇은 목록 · CSS · JS(components.html 안).
읽기(견본 파일·화면 파일)는 board_data.usage(Edge). 계약 contract/usage-map.md."""
import html as _html
import re

import specimen_parts

CLASS_ATTR = re.compile(r"""(?<![\w-])class\s*=\s*(?:"([^"]*)"|'([^']*)')""")
NO_CHIP = {"badge"}                                     # 배지는 screens.json badges 로 그린다 — 지도·칩 없음


def classes(src):
    out = set()
    for v in CLASS_ATTR.findall(src or ""):
        out.update((v[0] or v[1]).split())
    return out


def spec_keys(specimens_html):
    return [s["key"] for s in specimen_parts.sections(specimens_html or "")]


def usage(keys, screens):
    """keys = 견본 key 차례 · screens = [(화면 id, class 묶음)] 판 차례 → {key: [화면 id]} — 쓰는 화면이 없는 key·배지는 없다."""
    res = {}
    for k in keys:
        if k in NO_CHIP or k in res:
            continue
        ids = [sid for sid, cl in screens if k in cl]
        if ids:
            res[k] = ids
    return res


def label(n):
    return f"쓰는 화면 {n}"


def mark_section(open_tag, key, ids):
    """section.spec 여는 태그 → data-used(화면 id 빈칸으로)·id(spec-<key>, 없을 때) + 바로 뒤 머리 칩. 배지·0 = 그대로."""
    if key in NO_CHIP or not ids:
        return open_tag
    e = lambda s: _html.escape(str(s), quote=True)
    extra = f' data-used="{e(" ".join(ids))}"'
    if not re.search(r"""\bid\s*=""", open_tag):
        extra += f' id="spec-{e(key)}"'
    tag = open_tag[:-1].rstrip("/").rstrip() + extra + ">"
    chip = (f'<button type="button" class="use-chip" data-key="{e(key)}" title="판에서 이 부품을 쓰는 화면 보기">{label(len(ids))}</button>')
    return tag + chip


def index_html(entries):
    """[(key, title, 쓰는 화면 수)] → 맨 위 얇은 목록(이름 + 수, 누르면 그 section 으로). 없으면 빈 글."""
    if not entries:
        return ""
    e = lambda s: _html.escape(str(s), quote=True)
    links = "".join(f'<a class="use-link" href="#spec-{e(k)}"><span class="use-nm">{e(t)}</span><span class="use-n">{n}</span></a>' for k, t, n in entries)
    return f'<nav class="use-index" aria-label="부품 목록 · 쓰는 화면 수"><span class="use-h">부품 {len(entries)}</span>{links}</nav>'


# components.html 안 모양 — 견본 머리(.spec::before 제목) 오른쪽 끝 칩 · 맨 위 목록. 토큰이 없어도 보이게 기본값을 둔다
CSS = """
.spec[data-used]{position:relative}
.spec[id]{scroll-margin-top:16px}
.use-chip{position:absolute;top:0;right:0;height:26px;padding:0 10px;border:1px solid var(--c-line,#e3e3df);border-radius:999px;background:var(--c-surface,#fff);
  color:var(--c-text-2,#6b6b66);font:500 12px/24px system-ui,-apple-system,'Pretendard',sans-serif;cursor:pointer;white-space:nowrap}
.use-chip:hover{color:var(--c-text-1,#1c1c1c);border-color:var(--c-text-2,#8a8a85)}
.use-chip:focus-visible{outline:2px solid var(--c-brand,#2563eb);outline-offset:2px}
.use-index{display:flex;flex-wrap:wrap;align-items:center;gap:4px 6px;padding:0 0 4px;font:13px/1.3 system-ui,-apple-system,'Pretendard',sans-serif;color:var(--c-text-2,#6b6b66)}
.use-index .use-h{font-weight:600;color:var(--c-text-1,#1c1c1c);margin-right:6px}
.use-link{display:inline-flex;align-items:center;gap:6px;height:26px;padding:0 9px;border-radius:7px;color:inherit;text-decoration:none}
.use-link:hover{background:var(--c-surface,#fff);color:var(--c-text-1,#1c1c1c)}
.use-link .use-n{font-variant-numeric:tabular-nums;color:var(--c-text-3,#9a9a95);font-size:12px}
html.use-off .use-chip,html.use-off .use-index .use-n{display:none}
"""

# 칩 누르기 = 캔버스에 hd-usage-show {key, title} · 목록 누르기 = 그 section 으로 · 캔버스가 hd-usage-off 를 보내면 칩을 숨긴다(지도가 깨짐).
# window 잡는 단계 = palette.js 고르기 막기(document)보다 먼저 — 선택(V) 중에도 칩·목록은 그대로 눌린다
JS = """
(function(){
  function up(m){ try{ if(window.parent&&window.parent!==window) window.parent.postMessage(m,'*'); }catch(e){ console.warn('[hd] 캔버스에 알리지 못함 — '+e); } }
  addEventListener('click',function(e){
    var t=e.target; if(!t||!t.closest) return;
    var c=t.closest('.use-chip'), l=t.closest('.use-link'); if(!c&&!l) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if(c){ var s=c.closest('section'); up({type:'hd-usage-show', key:c.getAttribute('data-key')||'', title:s?(s.getAttribute('data-title')||''):''}); return; }
    var el=document.getElementById((l.getAttribute('href')||'').slice(1)); if(el) el.scrollIntoView({block:'start'});
  },true);
  addEventListener('message',function(e){ var d=e.data; if(d&&d.type==='hd-usage-off') document.documentElement.classList.add('use-off'); });
})();
"""
