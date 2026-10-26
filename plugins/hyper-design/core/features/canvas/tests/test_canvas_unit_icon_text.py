"""R15 후속 — 아이콘 + 여러 글 조각(글이 인라인 요소로 갈린 것) 글자 고치기 규칙(html_edit, I/O 없음).

규칙(html_edit._icon_text_patch · palette.js setIconText 같은 규칙):
- 글 묶음 = 바로 아래 글·br·글이 든 인라인 요소(b·span…)가 이어진 것. 글 없는 자식(svg·img·빈 i/span)은 아이콘 — 원문 그대로.
- 글 묶음이 하나이고 바뀐 곳이 글 마디 하나 안이면 그 마디만 고친다(b·span 같은 꾸밈 그대로).
- 그 밖(여러 마디에 걸친 바뀜 · 마디가 비게 됨 · 아이콘 사이 글 묶음 여럿)은 첫 글 묶음 = 앞뒤 공백 + 새 글(꾸밈 없음), 뒤 묶음은 비움.
- 거절: 글이 든 자식 중 인라인만으로 된 것이 아닌 것(블록·링크 a·글 안에 든 아이콘).
"""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import html_edit  # noqa: E402

BLOCK_REASON = "안에 다른 요소가 있어 글자만 바꿀 수 없어요"
SVG = '<svg viewBox="0 0 24 24"><path d="M19 12H5"/></svg>'


def edit(src, path, value):
    return html_edit.edit_html(src, [(path, "text", value)])


def test_change_inside_the_plain_run_keeps_the_bold_run():
    src = '<main><button>%s <b>뜻</b> 보기</button></main>' % SVG
    assert edit(src, "button", "뜻 보자") == '<main><button>%s <b>뜻</b> 보자</button></main>' % SVG


def test_change_inside_the_bold_run_patches_only_that_run():
    src = '<main><button>%s <b>뜻</b> 보기</button></main>' % SVG
    assert edit(src, "button", "의미 보기") == '<main><button>%s <b>의미</b> 보기</button></main>' % SVG


def test_icon_element_then_span_then_text():
    src = '<main><a class="n" href="x.html"><i class="ic"></i><span>다음</span> 단계</a></main>'
    assert edit(src, "a.n", "다음 단계로") == '<main><a class="n" href="x.html"><i class="ic"></i><span>다음</span> 단계로</a></main>'
    assert edit(src, "a.n", "다음! 단계") == '<main><a class="n" href="x.html"><i class="ic"></i><span>다음!</span> 단계</a></main>', "경계에 넣은 글은 앞 마디로"


def test_change_across_runs_becomes_plain_text_after_the_icon():
    src = '<main><button>%s <b>뜻</b> 보기</button></main>' % SVG
    assert edit(src, "button", "설명 열기") == '<main><button>%s 설명 열기</button></main>' % SVG
    assert edit(src, "button", "보기") == '<main><button>%s 보기</button></main>' % SVG, "꾸민 마디가 비면 꾸밈 없이"


def test_unchanged_text_leaves_the_file_alone():
    src = '<main><button>%s <b>뜻</b> 보기</button></main>' % SVG
    assert edit(src, "button", "뜻 보기") == src


def test_entities_in_the_edited_run_stay_escaped():
    src = '<main><p><svg></svg>A &amp; <b>B</b></p></main>'
    assert edit(src, "p", "A & C") == '<main><p><svg></svg>A &amp; <b>C</b></p></main>'
    assert edit(src, "p", "X & B") == '<main><p><svg></svg>X &amp; <b>B</b></p></main>'


def test_runs_between_icons_first_gets_the_text_rest_dropped():
    assert edit('<main><p><svg></svg><b>앞</b> 말<svg></svg>뒤</p></main>', "p", "하나") == '<main><p><svg></svg>하나<svg></svg></p></main>'


@pytest.mark.parametrize("src", [
    '<main><button><svg></svg><span><svg></svg>다음</span> 단계</button></main>',   # 글 조각 안에 아이콘 — 어디까지가 글인지 모호
    '<main><button><svg></svg> 다음 <div>블록</div></button></main>',
    '<main><button><svg></svg> 가기 <a href="x.html">링크</a></button></main>',
])
def test_ambiguous_structure_refuses(src):
    with pytest.raises(ValueError) as e:
        edit(src, "button", "x")
    assert BLOCK_REASON in str(e.value)
