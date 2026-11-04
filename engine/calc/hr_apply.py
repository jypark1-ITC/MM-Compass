"""인사 변동 입력(사이트 '인사 변동 제출') → 가동대상MM 반영

규칙: 가동대상MM = 그 달 재직 영업일 ÷ 전체 영업일 (휴직 기간 0) — 회사 인사자료와 같은 방식
- 입사(입사일)·복직(복직일): 그 날부터 가동대상. 인사자료에 이미 값이 있으면 인사자료 값이 우선(작은 쪽)
- 퇴사(퇴사일 = 마지막 근무일)·휴직(시작일): 그 뒤로 가동대상 0. 복직 입력이 있으면 그 날부터 다시 가동대상
- 조직이동(이동일, 새 소속): 이동일부터 새 팀에 가동대상이 잡힘 (새 소속을 가동인력목록에서 못 찾으면 적용 안 하고 확인 필요로 알림)
- 기타: 계산에 넣지 않음
이미 인사자료에 반영된 변동이면 같은 값이라 결과가 달라지지 않음 (겹쳐서 두 번 빠지지 않음)
"""
import datetime as dt, json, os, re
import pandas as pd

# 한국 공휴일 (2026) — 영업일 계산용
HOL = {dt.date(2026, 1, 1), dt.date(2026, 2, 16), dt.date(2026, 2, 17), dt.date(2026, 2, 18), dt.date(2026, 3, 2), dt.date(2026, 5, 1),
       dt.date(2026, 5, 5), dt.date(2026, 5, 25), dt.date(2026, 6, 3), dt.date(2026, 7, 17), dt.date(2026, 8, 17), dt.date(2026, 9, 24), dt.date(2026, 9, 25),
       dt.date(2026, 10, 5), dt.date(2026, 10, 9), dt.date(2026, 12, 25)}
M = [f"{m}월" for m in range(1, 13)]

def _bdays(y, m):
    d = dt.date(y, m, 1); out = []
    while d.month == m:
        if d.weekday() < 5 and d not in HOL: out.append(d)
        d += dt.timedelta(days=1)
    return out

def _norm(x): return re.sub(r"[\s_\-&()]", "", str(x or "")).lower().replace("팀", "").replace("사업부", "").replace("(직속)", "")
def _gid(x):
    try: return int(float(str(x).strip()))
    except Exception: return None
def _d(s):
    try: return dt.date.fromisoformat(str(s)[:10])
    except Exception: return None

def _ratio(y, m, ok):
    days = _bdays(y, m)
    return round(sum(1 for d in days if ok(d)) / len(days), 4) if days else 0.0

def _split(dept):
    p = [x.strip() for x in (dept or "").split("·")]
    return (p + ["", "", "", ""])[:4]

def apply(df, notes, year):
    """df: make_target 의 전체 행 (제외 포함). 반환: (df, 결과 목록)"""
    res = []
    notes = [n for n in notes if _d(n.get("date")) and _d(n["date"]).year == year and n.get("kind") in ("입사", "퇴사", "휴직", "복직", "조직이동")]
    if not notes: return df, res
    df = df.copy()
    live = df["제외"].fillna("") == ""
    # 사람별로 묶기: (법인, 이름, 사번 or 부서)
    groups = {}
    for n in sorted(notes, key=lambda n: (n["date"], n["id"])):
        k = (n["name"].strip(), str(n.get("sabun") or "").strip(), n["dept"])
        groups.setdefault(k, []).append(n)
    for (name, sabun, dept), ns in groups.items():
        corp, hq, dv, tm = _split(dept)
        cand = df[live & (df["성명"] == name)]
        if corp: cand = cand[cand["법인"] == corp]
        g = _gid(sabun)
        if g is not None and len(cand):
            c2 = cand[cand["그룹사번"].apply(_gid) == g]
            if len(c2): cand = c2
        elif len(cand) > 1:   # 동명이인: 부서(팀·사업부·본부)로 좁힘
            for col, v in (("팀", tm), ("사업부", dv), ("본부", hq)):
                if v:
                    c2 = cand[cand[col].apply(_norm) == _norm(v)]
                    if len(c2): cand = c2; break
            if cand["그룹사번"].apply(_gid).nunique() > 1:
                res.append(dict(ok=False, name=name, kind=ns[0]["kind"], date=ns[0]["date"], dept=dept, msg="같은 이름이 여러 명이라 누구인지 정하지 못했습니다 (사번을 넣어 주세요)")); continue
        kinds = {n["kind"] for n in ns}
        by = {k: [n for n in ns if n["kind"] == k] for k in kinds}
        if cand.empty and "입사" not in kinds:
            res.append(dict(ok=False, name=name, kind=ns[0]["kind"], date=ns[0]["date"], dept=dept, msg="가동인력목록·인사자료에서 이 사람을 찾지 못했습니다 (이름·부서 확인)")); continue
        # 구간 정리
        d_in = _d(by["입사"][0]["date"]) if "입사" in by else None
        d_out = _d(by["퇴사"][-1]["date"]) if "퇴사" in by else None
        leaves = []; rets = sorted(_d(n["date"]) for n in by.get("복직", []))
        for n in by.get("휴직", []):
            s = _d(n["date"]); e = next((r for r in rets if r > s), None); leaves.append((s, e))
        floor_from = [r for r in rets if not any(s < r and (e is None or e >= r) for s, e in leaves)]   # 휴직 입력 없이 복직만 있는 경우
        first = min(_d(n["date"]) for n in ns)
        has_floor = d_in is not None or bool(floor_from)
        def ok_day(d):
            if d_in and d < d_in: return False
            if d_out and d > d_out: return False
            for s, e in leaves:
                if d >= s and (e is None or d < e): return False
            if floor_from and not d_in and d < min(floor_from) and not leaves: return False
            return True
        # 이동: 소속 바꾸기 (조직이동)
        moved_ok = set(); moves = {}
        for n in by.get("조직이동", []):   # 같은 날짜 중복 입력은 하나로 (새 소속이 적힌 쪽을 남김)
            k_ = n["date"]
            if k_ not in moves or (n.get("to_org") or "").strip(): 
                if k_ not in moves or (n.get("to_org") or "").strip(): moves[k_] = n
        moves = list(moves.values())
        if cand.empty:   # 신규 입사 → 행 만들기
            gg = g if g is not None else 990000 + int(ns[0]["id"])
            r0 = dict(법인=corp or "아이티센클로잇", 본부=hq, 사업부=dv, 팀=tm, 성명=name, 그룹사번=str(gg), 입사일=str(d_in), 구분="정규직", 재직="재직",
                      출처="인사 변동 입력", 제외="", 비고="인사 변동 입력(입사)" + ("" if g is not None else " · 사번 미입력(임시 번호)"))
            for m in M: r0[m] = 0.0
            df = pd.concat([df, pd.DataFrame([r0])], ignore_index=True); live = df["제외"].fillna("") == ""
            cand = df.iloc[[len(df) - 1]]
        idxs = list(cand.index)
        before = {m: round(float(df.loc[idxs, m].sum()), 4) for m in M}
        for i in idxs:
            for mi, m in enumerate(M, 1):
                if (year, mi) < (first.year, first.month): continue
                comp = _ratio(year, mi, ok_day)
                ex = float(df.at[i, m] or 0)
                if has_floor: new = comp if ex < 0.0001 else min(ex, comp)
                else: new = min(ex, comp)
                df.at[i, m] = round(new, 4)
        # 조직이동: 이동일 이후는 새 팀으로
        for n in moves:
            dmv = _d(n["date"]); to = (n.get("to_org") or "").strip()
            to = re.sub(r"(으)?로\s*(전배|이동|전적|발령)?\s*$|\s*(전배|이동|전적|발령)\s*$", "", to).strip()   # "CENI운영팀으로 전배" → "CENI운영팀"
            tgt = df[live & (df["팀"].apply(_norm) == _norm(to))] if to else df.iloc[0:0]
            if tgt.empty and to: tgt = df[live & (df["사업부"].apply(_norm) == _norm(to))]
            if tgt.empty and _norm(to):   # 문장으로 적은 경우: 글 안에 들어 있는 팀 이름을 찾음 (가장 긴 이름)
                names = sorted({t_ for t_ in df.loc[live, "팀"].dropna().unique() if len(_norm(t_)) >= 2 and _norm(t_) in _norm(to)}, key=lambda t_: -len(_norm(t_)))
                if names: tgt = df[live & (df["팀"] == names[0])]
            if tgt.empty:
                res.append(dict(ok=False, name=name, kind="조직이동", date=n["date"], dept=dept, msg=f"새 소속 '{to or '(비어 있음)'}'을 가동인력목록에서 찾지 못해 적용하지 못했습니다 (팀 이름을 그대로 적어 주세요)")); continue
            t0 = tgt.iloc[0]; src = df.loc[idxs[0]]
            same_p = df[live & (df["법인"] == src["법인"]) & ((df["그룹사번"].apply(_gid) == _gid(src["그룹사번"])) if _gid(src["그룹사번"]) is not None else (df["성명"] == name))]
            there = same_p[(same_p["팀"] == t0["팀"]) & (same_p["사업부"] == t0["사업부"])]
            if len(there) and float(there[[M[i] for i in range(dmv.month - 1, 12)]].sum().sum()) > 0.001:   # 인사자료에 이미 새 소속으로 들어 있음
                # 이전 소속(가동인력목록)에 같은 사람 값이 이동일 이후에도 남아 있으면 0으로 정리 → 두 팀에 이중 집계되지 않게 (2026-11-03)
                f_ = _ratio(year, dmv.month, lambda d: d >= dmv); cut = []
                for i in idxs:
                    if i in there.index: continue
                    for mi, m in enumerate(M, 1):
                        if mi < dmv.month: continue
                        old_v = float(df.at[i, m] or 0); new_v = round(old_v * (1 - f_), 4) if mi == dmv.month else 0.0
                        if abs(old_v - new_v) > 0.0001: df.at[i, m] = new_v; cut.append(f"{m} {old_v:.2f}→{new_v:.2f}")
                res.append(dict(ok=True, name=name, kind="조직이동", date=n["date"], dept=dept, team=str(t0["팀"]),
                                msg=(f"인사자료에 이미 {t0['팀']}으로 들어 있음 · 이전 소속 값 정리: " + " · ".join(cut)) if cut else f"인사자료에 이미 {t0['팀']}으로 들어 있어 달라지는 것 없음"))
                moved_ok.add(id(n)); continue
            row = {c: src[c] for c in df.columns}; row.update(법인=t0["법인"], 본부=t0["본부"], 사업부=t0["사업부"], 팀=t0["팀"], 출처="인사 변동 입력", 비고="조직이동 " + n["date"])
            for mi, m in enumerate(M, 1):
                ex = sum(float(df.at[i, m] or 0) for i in idxs)   # 이 사람 행이 둘 이상이어도 합쳐서 옮김
                if mi < dmv.month: row[m] = 0.0
                elif mi == dmv.month:
                    f_ = _ratio(year, mi, lambda d: d >= dmv); row[m] = round(ex * f_, 4)
                    for i in idxs: df.at[i, m] = round(float(df.at[i, m] or 0) * (1 - f_), 4)
                else:
                    row[m] = ex
                    for i in idxs: df.at[i, m] = 0.0
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            live = df["제외"].fillna("") == ""
        after = {m: round(float(df.loc[idxs, m].sum()), 4) for m in M}
        diffs = [f"{m} {before[m]:.2f}→{after[m]:.2f}" for m in M if abs(before[m] - after[m]) > 0.004]
        for n in ns:
            if n["kind"] == "조직이동" and (n not in moves or id(n) in moved_ok or any(r["name"] == name and r["kind"] == "조직이동" and r["date"] == n["date"] for r in res)): continue
            res.append(dict(ok=True, name=name, kind=n["kind"], date=n["date"], dept=dept, team=str(df.at[idxs[0], "팀"] or df.at[idxs[0], "사업부"] or ""),
                            msg=(" · ".join(diffs) if diffs else "인사자료에 이미 같은 값으로 들어 있어 달라지는 것 없음")))
    return df, res
