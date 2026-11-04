# 인원 단위 집계: 가동대상(인원별 MM) + 투입(인원별·프로젝트별 MM) + 당월 인사 변동
import pandas as pd, warnings, datetime as dt
from real_data import NP_HEADS
warnings.filterwarnings("ignore")
SP = __import__('cfg').WORK
UP = ""
M = 12
CUR = __import__("cfg").CUR   # 당월 (1~12)
PCOL, CCOL = (f"{CUR - 1}월" if CUR > 1 else f"{CUR}월"), f"{CUR}월"   # 전월 · 당월 가동대상 열

def gid(x):
    try: return int(float(str(x).strip()))
    except Exception: return None

def org_label(hq, dv, tm):
    """직속 표기 없이 실제 조직명"""
    if tm and tm != "(직속)": return tm
    if dv and dv != "(직속)": return dv
    return hq

def load():
    t = pd.read_pickle(SP + "use_target.pkl").copy()
    t.loc[t["사업부"] == "AX-Eng사업부", "사업부"] = "AX Consulting & Eng 사업부"
    c = pd.read_pickle(SP + "use_clo_plan.pkl").copy(); c["법인"] = "아이티센클로잇"
    e = pd.read_pickle(SP + "use_et_plan.pkl").copy(); e["법인"] = "아이티센엔텍"
    i = pd.concat([c, e], ignore_index=True)
    MC = [f"2026년_{m}월" for m in range(1, 13)]
    i[MC] = i[MC].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    # 직무·직급 보조 정보
    attr = {}
    cl = pd.read_excel(__import__('cfg').inp("target_clo"))
    et = pd.read_excel(__import__('cfg').inp("target_et"))
    for df, corp in ((cl, "아이티센클로잇"), (et, "아이티센엔텍")):
        for _, r in df.iterrows():
            attr[(corp, gid(r["그룹사번"]))] = dict(직급=r.get("직급"), 직무=r.get("직무"), 직책=r.get("직책"))
    h = pd.read_excel(SP + "hr.xlsx", header=None)
    cols = []
    for a, b in zip(h.iloc[0].ffill(), h.iloc[1]): cols.append(f"{a}_{b}" if isinstance(b, str) and b.endswith(("월", "계")) else a)
    hd = h.iloc[2:].copy(); hd.columns = cols
    for _, r in hd.iterrows():
        attr.setdefault(("아이티센클로잇", gid(r["그룹사번"])), dict(직급=r.get("직급"), 직무=r.get("직무"), 직책=r.get("직책")))
    return t, i, MC, attr, cl, et, hd

def people():
    t, i, MC, attr, cl, et, hd = load()
    P = {}
    for _, r in t.iterrows():
        k = (r["법인"], gid(r["그룹사번"]))
        p = P.setdefault(k, dict(corp=r["법인"], gid=k[1], name=r["성명"], T=[0.0]*M, inp=[0.0]*M, ex=[0.0]*M, rd=[0.0]*M, pr=[0.0]*M,
                                 exec=False, rows=[], projs={}, 구분=r["구분"]))
        for m in range(M): p["T"][m] += float(r[f"{m+1}월"])
        if (r["법인"], r["성명"]) in NP_HEADS: p["exec"] = True
        p["rows"].append((float(r[CCOL]), float(r[PCOL]), r["본부"], r["사업부"], r["팀"]))
        _tk = p.setdefault("tmT", {}).setdefault((r["본부"], r["사업부"], r["팀"]), [0.0]*M)   # 팀별 월 가동대상 (이동한 사람의 대기를 그 팀에 있던 달에만 보이려고)
        for m in range(M): _tk[m] += float(r[f"{m+1}월"])
    for _, r in i.iterrows():
        k = (r["법인"], gid(r["그룹사번"]))
        p = P.get(k)
        if p is None:
            p = P.setdefault(k, dict(corp=r["법인"], gid=k[1], name=r["성명"], T=[0.0]*M, inp=[0.0]*M, ex=[0.0]*M, rd=[0.0]*M, pr=[0.0]*M,
                                     exec=False, rows=[(0, 0, r["본부"], r["사업부"], r["팀"])], projs={}, 구분=r["정규직/계약직"]))
        f = {"이행": "ex", "제안": "pr", "R&D·내부과제": "rd"}.get(r["구분"])
        mm = [float(r[c]) for c in MC]
        for m in range(M):
            p["inp"][m] += mm[m]
            if f: p[f][m] += mm[m]
        if sum(mm) > 0:
            pk = (r["코드"], r["PJT 명"], r["구분"])
            cur = p["projs"].setdefault(pk, [0.0]*M)
            for m in range(M): cur[m] += mm[m]
    for p in P.values():
        best = sorted(p["rows"], key=lambda x: (x[0], x[1]), reverse=True)[0]
        p["hq"], p["dv"], p["tm"] = best[2], best[3], best[4]
        p["org"] = org_label(p["hq"], p["dv"], p["tm"])
        a = attr.get((p["corp"], p["gid"]), {})
        p.update(직급=a.get("직급") if pd.notna(a.get("직급")) else "", 직무=a.get("직무") if pd.notna(a.get("직무")) else "")
        p["idle"] = [round(max(0.0, a_ - b_), 4) for a_, b_ in zip(p["T"], p["inp"])]
    return P

def _d(x):
    if pd.isna(x) or x in ("", None): return None
    try: return pd.to_datetime(x).date()
    except Exception: return None

def events(year=2026, month=None):
    month = month or CUR
    """당월 인사 변동 (입사·퇴사·휴직·복직·전입·전출) — 가동인력목록(클로잇·엔텍 ENT) + 통합인사정보(AX)"""
    t, i, MC, attr, cl, et, hd = load()
    lo = dt.date(year, month, 1); hi = (dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)) - dt.timedelta(days=1)
    lo_q = lo - dt.timedelta(days=1)   # 전월 말일 퇴사 = 당월부터 제외
    while lo_q.weekday() >= 5: lo_q -= dt.timedelta(days=1)   # 말일이 주말이면 마지막 영업일(금)까지 (예: 10/30 퇴사 → 11월 인사변동에 표시)
    tgt = {}
    for _, r in t.iterrows():
        k = (r["법인"], gid(r["그룹사번"])); v = tgt.setdefault(k, [0.0, 0.0])
        v[0] += float(r[f"{month - 1}월"]) if month > 1 else 0.0; v[1] += float(r[f"{month}월"])
    ev = []
    def add(kind, corp, r, d, org, note=""):
        k = (corp, gid(r["그룹사번"])); m9, m10 = tgt.get(k, (0.0, 0.0))
        ev.append(dict(kind=kind, corp=corp, name=r["성명"], org=org, date=d, m9=m9, m10=m10, note=note))
    def scan(df, corp, orgf, typef):
        for _, r in df.iterrows():
            org = orgf(r)
            if typef(r) == "계약직(일반)": continue
            ji, qi = _d(r.get("입사일")), _d(r.get("퇴사일"))
            hs, he = _d(r.get("휴직시작일")), _d(r.get("휴직종료일"))
            ai, ao = _d(r.get("발령(전입)일자")), _d(r.get("발령(전출)일자"))
            if ji and lo <= ji <= hi: add("입사", corp, r, ji, org)
            if qi and lo_q <= qi <= hi: add("퇴사", corp, r, qi, org)
            if hs and lo <= hs <= hi: add("휴직", corp, r, hs, org, f"~ {he:%Y.%m.%d}" if he else "")
            if he and lo_q <= he < hi: add("복직", corp, r, he + dt.timedelta(days=1), org, "휴직 종료")
            if ai and lo <= ai <= hi and ai != ji: add("전입", corp, r, ai, org)
            if ao and lo_q <= ao <= hi and ao != qi: add("전출", corp, r, ao + dt.timedelta(days=1) if ao < lo else ao, org)
    def clo_org(r):
        s = [x for x in str(r["조직"]).split("_")[1:] if x not in ("CLO", "CSO")]
        return " · ".join(dict.fromkeys(s))
    cl2 = cl[~cl["조직"].astype(str).str.startswith("ITC-JAPAN")]   # AX 행도 포함 (AX↔타 본부 전배 감지)
    scan(cl2, "아이티센클로잇", clo_org, lambda r: r["정규직/계약직"])
    et2 = et[et["조직"].astype(str).str.startswith("ET_ENT")]
    scan(et2, "아이티센엔텍", lambda r: " · ".join(str(r["조직"]).split("_")[1:]), lambda r: r["정규직/계약직"])
    hd2 = hd[(hd["관리법인"] != "SS")]
    hd2 = hd2.assign(**{"발령(전입)일자": None, "발령(전출)일자": None})
    scan(hd2.drop_duplicates("그룹사번", keep="last"), "아이티센클로잇",
         lambda r: " · ".join(x for x in ["AX사업본부", str(r["사업부"]).split("_")[-1], str(r["팀"]).split("_")[-1]] if x and x != "nan"),
         lambda r: "계약직(일반)" if r["직원구분"] not in ("정규직", "촉탁직", "임원") else "")
    # 사이트 '인사 변동 제출'(반영)의 조직이동 중 목록·인사자료의 전입/전출일자로 잡히지 않은 것 → 전출+전입으로 추가 (표에서 '전배'로 합쳐짐)
    try:
        import cfg as _cfg
        for n_ in _cfg.HR_NOTES:
            if n_.get("kind") != "조직이동" or n_.get("status") not in (None, "반영"): continue
            nd = _d(n_.get("date"))
            if not nd or not (lo <= nd <= hi): continue
            if any(e_["name"] == n_["name"] and e_["kind"] in ("전입", "전출") and abs((e_["date"] - nd).days) <= 3 for e_ in ev): continue
            parts = [x.strip() for x in str(n_["dept"]).split(" · ")]
            corp_ = parts[0]; src_org = " · ".join(x for x in parts[1:] if x != "(직속)")
            hit = hd2[hd2["성명"] == n_["name"]]
            if hit.empty: continue
            r_ = hit.iloc[-1]
            dst_org = " · ".join(x for x in ["AX사업본부", str(r_["사업부"]).split("_")[-1], str(r_["팀"]).split("_")[-1]] if x and x != "nan")
            if dst_org == src_org: continue
            add("전출", corp_, r_, nd, src_org); add("전입", corp_, r_, nd, dst_org)
    except Exception as ex_:
        print("hr notes events skip:", ex_)
    seen = set(); out = []
    for e_ in sorted(ev, key=lambda x: (x["date"], x["kind"])):
        k = (e_["kind"], e_["name"], e_["date"])
        if k in seen: continue
        seen.add(k); out.append(e_)
    return out

if __name__ == "__main__":
    P = people()
    print(len(P), sum(1 for p in P.values() if sum(p["idle"][9:]) > 0.05))
    for e_ in events(): print(e_)
