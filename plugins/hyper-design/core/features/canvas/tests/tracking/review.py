"""검토 과정 돌아보기 — 과한 테스트·게이트가 구현을 느리게 하는 곳을 찾는다(약 1초, 브라우저 없음).

python3 tests/tracking/review.py [--days 7]

읽는 것: process.json(조각마다 손으로 적는 비용·값어치) · runs.json(conftest 가 테스트를 돌릴 때마다 자동으로 적음)
보이는 것: 조각별 테스트 시간·전체 실행 수·게이트 걸림(진짜/잡음)·낭비, 그리고 policy 를 넘은 곳과 고칠 점.
"""
import argparse, json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, default):
    p = HERE / name
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except ValueError as e:
        sys.exit(f"{name} 를 읽을 수 없음: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7)
    a = ap.parse_args()
    proc, runs = load("process.json", {"policy": {}, "slices": []}), load("runs.json", [])
    pol, out, flags = proc.get("policy", {}), [], []

    out.append("조각        테스트분  전체  게이트(진짜/잡음)  잡은 버그(새/전체)  낭비분")
    rules = defaultdict(lambda: {"real": 0, "noise": 0, "min": 0})
    total_t = total_w = 0
    for s in proc.get("slices", []):
        t, g = s.get("tests", {}), s.get("gate", {})
        fired = g.get("fired", [])
        real = sum(f.get("verdict") == "real" for f in fired)
        noise = sum(f.get("verdict") == "noise" for f in fired)
        for f in fired:
            r = rules[f.get("rule", "?")]; r[f.get("verdict", "noise")] += 1; r["min"] += f.get("minutes", 0)
        caught = Counter(c.get("by") for c in s.get("caught", []))
        waste = sum(w.get("minutes", 0) for w in s.get("waste", []))
        total_t += t.get("minutes", 0); total_w += waste
        out.append(f"{s['slice']:<10}  {t.get('minutes', 0):>7.1f}  {t.get('full', 0):>4}  {real:>8}/{noise:<8}  {caught.get('new-test', 0):>9}/{caught.get('full', 0):<8}  {waste:>5}")
        lim = pol.get("max_full_per_numbered_slice", 1) if s.get("numbered") else pol.get("full_runs_in_sub_slice", 0)
        if t.get("full", 0) > lim:
            flags.append(f"[{s['slice']}] 전체 실행 {t['full']}회 > 한도 {lim} ({'번호' if s.get('numbered') else '하위'} 조각)")
        gmin = sum(f.get("minutes", 0) for f in fired)
        if gmin > pol.get("gate_minutes_per_slice", 10):
            flags.append(f"[{s['slice']}] 게이트 대응 {gmin}분 > {pol['gate_minutes_per_slice']}분")
    out.append(f"합계 테스트 {total_t:.1f}분 · 그중 낭비 {total_w}분 ({(100 * total_w / total_t) if total_t else 0:.0f}%)")

    out.append("\n게이트 규칙별")
    for name, r in sorted(rules.items()):
        out.append(f"  {name}: 진짜 {r['real']} · 잡음 {r['noise']} · 대응 {r['min']}분")
        if r["noise"] and r["noise"] >= r["real"] * pol.get("gate_noise_max_ratio", 1.0):
            flags.append(f"게이트 '{name}': 잡음 {r['noise']} ≥ 진짜 {r['real']} — 규칙을 줄이거나 다듬을 후보")

    cut = time.time() - a.days * 86400
    recent = [r for r in runs if time.mktime(time.strptime(r["at"], "%Y-%m-%dT%H:%M:%S")) >= cut]
    if recent:
        by = defaultdict(lambda: [0, 0.0])
        for r in recent:
            by[r["scope"]][0] += 1; by[r["scope"]][1] += r.get("sec", 0)
        out.append(f"\n최근 {a.days:g}일 실행(runs.json): " + " · ".join(f"{k} {n}회 {s / 60:.1f}분" for k, (n, s) in sorted(by.items())))
        fulls = [r for r in recent if r["scope"] == "full"]
        win = pol.get("repeat_full_within_min", 60) * 60
        for x, y in zip(fulls, fulls[1:]):
            gap = time.mktime(time.strptime(y["at"], "%Y-%m-%dT%H:%M:%S")) - time.mktime(time.strptime(x["at"], "%Y-%m-%dT%H:%M:%S"))
            if gap < win:
                flags.append(f"전체 실행이 {gap / 60:.0f}분 만에 다시({x['at']} → {y['at']}) — 실패 뒤라면 --lf 로 충분했는지")
        for r in fulls:
            if r["failed"]:
                flags.append(f"전체 실행 실패 {len(r['failed'])}개({r['at']}): {', '.join(r['failed'][:5])} — 큰 실행 전 grep 으로 찾을 수 있었는지")

    out.append("\n걸린 곳" if flags else "\n걸린 곳 없음")
    out += ["  - " + f for f in flags]
    print("\n".join(out))


if __name__ == "__main__":
    main()
