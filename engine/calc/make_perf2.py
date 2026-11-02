import pandas as pd, warnings, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
warnings.filterwarnings('ignore')
SRC = __import__('cfg').inp("sold_clo")
OUT = __import__('cfg').w("report_clo.xlsx")
LAST = __import__('cfg').ACT.get("clo", __import__('cfg').CI)   # 실적 확정 월 (1~LAST월 = 'Activity 실적(누적)'과 일치 — run.py 가 판별)
MON = list(range(1, LAST+1))

h = pd.read_excel(SRC, header=None); cols = []
for a, b in zip(h.iloc[0], h.iloc[1]):
    cols.append(f"{str(a)[:5]}_{b}" if str(a).startswith(("2026년", "2027년")) else a)
d = h.iloc[2:].copy(); d.columns = cols; d = d.reset_index(drop=True)
MC = [f"2026년_{m}월" for m in MON]
d[MC] = d[MC].astype(float)

def parse_org(s):
    t = [x for x in str(s).split("_")]
    corp = t[0]; rest = []
    for x in t[1:]:
        if x in ("CLO", "CSO", "ITC-JAPAN") or x in rest: continue
        rest.append(x)
    hq = rest[0] if rest else ""
    dv = next((x for x in rest[1:] if x.endswith("사업부")), "")
    tm = next((x for x in rest[1:] if not x.endswith("사업부")), "")
    return corp, hq, dv, tm
po = d["조직"].apply(parse_org)
d["법인구분"] = po.str[0]; d["본부"] = po.str[1]; d["사업부"] = po.str[2]; d["팀"] = po.str[3]
# AI이노베이션센터 → AX사업본부 > AX Consulting & Eng 사업부 > AX엔지니어링팀 (전적 이관, 이행 처리)
d["이관"] = d["본부"] == "AI이노베이션센터"
d["원소속"] = d["조직"].where(d["이관"], "")
d.loc[d["이관"], ["본부", "사업부", "팀"]] = ["AX사업본부", "AX Consulting & Eng 사업부", "AX엔지니어링팀"]
d["코드"] = d["PJT 코드"].fillna("").astype(str)
d["끝자리"] = d["코드"].str[-1].where(d["코드"] != "", "")

SUF = {"C": "이행", "W": "이행", "P": "제안", "I": "R&D·내부과제", "N": "R&D·내부과제"}
def classify(r):
    if r["이관"]:
        if r["끝자리"] == "P": return "제안", "AI이노베이션센터 → AX엔지니어링팀 이관 (제안 유지)"
        return "이행", "AI이노베이션센터 → AX엔지니어링팀 이관 · R&D → 이행 처리"
    # (동행복권 Next Gen → R&D 규칙은 아이티센엔텍에만 적용 · 클로잇은 코드 그대로 이행)
    if r["사업유형"] == "비매출": return "R&D·내부과제", "사업유형 비매출"
    if r["끝자리"] in SUF: return SUF[r["끝자리"]], ""
    return "", "코드 없음"
cl = d.apply(classify, axis=1, result_type="expand"); d["구분"] = cl[0]; d["분류근거"] = cl[1]

def excl(r):
    if r["법인구분"] == "ITC-JAPAN": return "아이티센재팬(JAPAN) 제외"
    if r["팀"] == "AX엔지니어링팀(공공)": return "관리법인 SS (AX엔지니어링팀(공공)) 제외"
    if r["정규직/계약직"] == "계약직(일반)": return "계약직(일반) 제외"
    if r["코드"] == "": return "프로젝트 없음 (MM 0)"
    return ""
d["제외사유"] = d.apply(excl, axis=1)
d["시스템구분"] = d["PJT 구분"].fillna("")
d["재분류"] = (d["구분"] != "") & (d["시스템구분"] != "") & (d["구분"] != d["시스템구분"].replace({"무상유지보수": "이행"}))
use = d[d["제외사유"] == ""].copy()
use.loc[use["사업부"] == "", "사업부"] = "(직속)"; use.loc[use["팀"] == "", "팀"] = "(직속)"
# 통계에 '사업부 직속' 행이 없는 경우 → 통계와 같이 그 사업부의 첫 팀으로 귀속
import sys as _s; _s.path.insert(0, __import__('cfg').CALC)
from stats_parse import parse_stats as _ps
_SB = _ps()
_direct = {(b["hq"], b["dv"]) for b in _SB if not b["tm"]}
_first = {}
for b in _SB:
    if b["tm"]: _first.setdefault((b["hq"], b["dv"]), b["tm"])
_m = (use["팀"] == "(직속)") & (use["사업부"] != "(직속)") & ~use.apply(lambda r: (r["본부"], r["사업부"]) in _direct, axis=1)
DIRECT_EXTRA = {}
for (hq_, dv_), grp in use[_m].groupby(["본부", "사업부"]):
    DIRECT_EXTRA[(hq_, dv_)] = [round(float(grp[f"2026년_{m}월"].sum()), 4) for m in MON]
ex = d[d["제외사유"] != ""].copy()

# ---------------- workbook ----------------
FN = "맑은 고딕"
f0 = Font(name=FN, size=10); fb = Font(name=FN, size=10, bold=True); fh = Font(name=FN, size=10, bold=True, color="FFFFFF")
ft = Font(name=FN, size=14, bold=True, color="0F2942"); fm = Font(name=FN, size=9, color="6B7280")
navy = PatternFill("solid", fgColor="3D5D84"); sub = PatternFill("solid", fgColor="E8EEF5"); tot = PatternFill("solid", fgColor="D5DEEA")
thin = Side(style="thin", color="D0D7E0"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
C = Alignment(horizontal="center", vertical="center", wrap_text=True); Lft = Alignment(horizontal="left", vertical="center")
NF = "0.00"
wb = openpyxl.Workbook()

def hdr(ws, r, names):
    for i, n in enumerate(names, 1):
        c = ws.cell(row=r, column=i, value=n); c.font = fh; c.fill = navy; c.alignment = C; c.border = box
def autofit(ws, minw=6, maxw=60):
    w = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is None: continue
            v = str(c.value)
            if v.startswith("="): v = "0000.00"
            n = sum(2 if ord(ch) > 127 else 1 for ch in v) + 2
            w[c.column_letter] = max(w.get(c.column_letter, 0), n)
    for k, v in w.items(): ws.column_dimensions[k].width = max(minw, min(maxw, v))

# 1) 가공데이터 (계산 기준이 되는 행)
g = wb.active; g.title = "가공데이터"
GC = ["본부", "사업부", "팀", "성명", "그룹사번", "정규직/계약직", "재직여부", "PJT 코드", "PJT 명", "시스템구분", "구분", "분류근거"] + [f"{m}월" for m in MON] + [f"1~{LAST}월 합계"]
hdr(g, 1, GC)
for i, (_, r) in enumerate(use.iterrows(), 2):
    vals = [r["본부"], r["사업부"], r["팀"], r["성명"], str(r["그룹사번"]), r["정규직/계약직"], r["재직여부"], r["코드"], r["PJT 명"], r["시스템구분"], r["구분"], r["분류근거"]]
    for j, v in enumerate(vals, 1):
        c = g.cell(row=i, column=j, value=v); c.font = f0; c.border = box
    for k, m in enumerate(MON):
        c = g.cell(row=i, column=13+k, value=round(float(r[f"2026년_{m}월"]), 4)); c.number_format = NF; c.font = f0; c.border = box; c.alignment = C
    c = g.cell(row=i, column=13+len(MON), value=f"=SUM({L(13)}{i}:{L(12+len(MON))}{i})"); c.number_format = NF; c.font = fb; c.border = box; c.alignment = C
    if r["분류근거"]: g.cell(row=i, column=12).font = Font(name=FN, size=10, color="A2551B", bold=True)
NG = len(use) + 1
g.freeze_panes = "E2"; g.auto_filter.ref = f"A1:{L(13+len(MON))}{NG}"
autofit(g); g.column_dimensions["I"].width = 48

R = lambda col: f"가공데이터!${col}$2:${col}${NG}"
COLM = {m: L(12+k+1) for k, m in enumerate(MON)}
KINDS = ["이행", "제안", "R&D·내부과제"]
HQS = [h_ for h_ in use.groupby("본부")[f"2026년_{LAST}월"].sum().sort_values(ascending=False).index]

# 2) 요약 (9월 + 누계) — SUMIFS
s = wb.create_sheet("요약", 0)
s["A1"] = f"2026년 {LAST}월 실적 (MM) · 아이티센클로잇"; s["A1"].font = ft
s["A2"] = "출처: SOLD투입MM목록_20261002 · JAPAN·계약직(일반) 제외 · 구분 = 코드 끝자리 (C·W 이행 / P 제안 / I·N R&D·내부과제), 사업유형 비매출 = R&D·내부과제"; s["A2"].font = fm
hdr(s, 4, ["본부", f"{LAST}월 이행", f"{LAST}월 제안", f"{LAST}월 R&D·내부과제", f"{LAST}월 합계", "", f"1~{LAST}월 이행", f"1~{LAST}월 제안", f"1~{LAST}월 R&D·내부과제", f"1~{LAST}월 합계"])
s.cell(row=4, column=6).fill = PatternFill(None); s.cell(row=4, column=6).border = Border()
for i, hq in enumerate(HQS, 5):
    s.cell(row=i, column=1, value=hq).font = fb
    for k, kd in enumerate(KINDS):
        c = s.cell(row=i, column=2+k, value=f'=SUMIFS({R(COLM[LAST])},{R("A")},$A{i},{R("K")},"{kd}")')
        c2 = s.cell(row=i, column=7+k, value=f'=SUMIFS({R(L(13+len(MON)))},{R("A")},$A{i},{R("K")},"{kd}")')
    s.cell(row=i, column=5, value=f"=SUM(B{i}:D{i})"); s.cell(row=i, column=10, value=f"=SUM(G{i}:I{i})")
    for j in (2,3,4,5,7,8,9,10):
        c = s.cell(row=i, column=j); c.number_format = NF; c.alignment = C; c.border = box; c.font = fb if j in (5, 10) else f0
    s.cell(row=i, column=1).border = box
tr = 5 + len(HQS)
s.cell(row=tr, column=1, value="합계").font = fb
for j in (2,3,4,5,7,8,9,10):
    c = s.cell(row=tr, column=j, value=f"=SUM({L(j)}5:{L(j)}{tr-1})"); c.number_format = NF; c.font = fb; c.fill = tot; c.alignment = C; c.border = box
s.cell(row=tr, column=1).fill = tot; s.cell(row=tr, column=1).border = box
s.cell(row=tr+2, column=1, value=f"※ 1~{LAST}월은 파일의 'Activity 실적(누적)'과 월별 합이 전 행 일치 → 실적 확정 구간. {LAST+1}월 이후 값은 계획이라 제외했습니다.").font = fm
s.cell(row=tr+3, column=1, value="※ 제외·재분류 내역은 '제외·재분류' 시트, 계산에 쓰인 행은 '가공데이터' 시트에서 확인할 수 있습니다.").font = fm
autofit(s); s.column_dimensions["F"].width = 2; s.column_dimensions["A"].width = 22

# 3) 월별 (본부 × 구분 × 월)
m_ = wb.create_sheet("월별", 1)
m_["A1"] = "본부 · 구분별 월 실적 (MM)"; m_["A1"].font = ft
hdr(m_, 3, ["본부", "구분"] + [f"{m}월" for m in MON] + ["합계"])
r = 4
for hq in HQS:
    start = r
    for kd in KINDS + ["소계"]:
        m_.cell(row=r, column=1, value=hq if kd == KINDS[0] else None).font = fb
        m_.cell(row=r, column=2, value=kd).font = fb if kd == "소계" else f0
        for k, mo in enumerate(MON):
            if kd == "소계": f = f"=SUM({L(3+k)}{start}:{L(3+k)}{r-1})"
            else: f = f'=SUMIFS({R(COLM[mo])},{R("A")},"{hq}",{R("K")},"{kd}")'
            c = m_.cell(row=r, column=3+k, value=f); c.number_format = NF; c.alignment = C
        c = m_.cell(row=r, column=3+len(MON), value=f"=SUM(C{r}:{L(2+len(MON))}{r})"); c.number_format = NF; c.font = fb; c.alignment = C
        for j in range(1, 4+len(MON)):
            m_.cell(row=r, column=j).border = box
            if kd == "소계": m_.cell(row=r, column=j).fill = sub
        r += 1
for k in range(len(MON) + 1):
    col = 3 + k
    c = m_.cell(row=r, column=col, value=f'=SUMIFS({L(col)}4:{L(col)}{r-1},$B$4:$B${r-1},"소계")'); c.number_format = NF; c.font = fb; c.fill = tot; c.alignment = C; c.border = box
m_.cell(row=r, column=1, value="합계").font = fb; m_.cell(row=r, column=1).fill = tot; m_.cell(row=r, column=2).fill = tot
m_.freeze_panes = "C4"; autofit(m_); m_.column_dimensions["A"].width = 20

# 4) 9월 상세 (부서 > 성명 > 프로젝트 — 기존 피벗 형식)
p = wb.create_sheet(f"{LAST}월_상세", 2)
p["A1"] = f"{LAST}월 실적 상세 · 부서 › 성명 › 프로젝트"; p["A1"].font = ft
hdr(p, 3, ["본부", "사업부", "팀", "성명", "PJT 코드", "PJT 명", "R&D·내부과제", "이행", "제안", "합계"])
x = use[use[f"2026년_{LAST}월"] > 0].sort_values(["본부", "사업부", "팀", "성명", "코드"])
r = 4
for _, rr in x.iterrows():
    vals = [rr["본부"], rr["사업부"], rr["팀"], rr["성명"], rr["코드"], rr["PJT 명"]]
    for j, v in enumerate(vals, 1): p.cell(row=r, column=j, value=v).font = f0
    v = float(rr[f"2026년_{LAST}월"])
    for j, kd in zip((7, 8, 9), ("R&D·내부과제", "이행", "제안")):
        c = p.cell(row=r, column=j, value=round(v, 4) if rr["구분"] == kd else None); c.number_format = NF; c.alignment = C
    c = p.cell(row=r, column=10, value=f"=SUM(G{r}:I{r})"); c.number_format = NF; c.font = fb; c.alignment = C
    for j in range(1, 11): p.cell(row=r, column=j).border = box
    r += 1
for j in (7, 8, 9, 10):
    c = p.cell(row=r, column=j, value=f"=SUM({L(j)}4:{L(j)}{r-1})"); c.number_format = NF; c.font = fb; c.fill = tot; c.alignment = C; c.border = box
p.cell(row=r, column=1, value="합계").font = fb
p.freeze_panes = "E4"; p.auto_filter.ref = f"A3:J{r-1}"; autofit(p); p.column_dimensions["F"].width = 48

# 4-2) 조직별 월별 — 통계 형식 (가동대상MM · 이행 · 제안 · R&D · 대기 · 가동률 · 가득률)
import sys; sys.path.insert(0, __import__('cfg').CALC)
from stats_parse import parse_stats
SB = parse_stats()
for (hq_, dv_), ext in DIRECT_EXTRA.items():
    t_ = _first.get((hq_, dv_))
    idx = next(i for i, b in enumerate(SB) if b["hq"] == hq_ and b["dv"] == dv_)
    for b in SB:
        if b["hq"] == hq_ and b["dv"] == dv_ and b["tm"] == t_:
            b["vals"]["가동MM"] = [v - (ext[k] if k < len(ext) else 0) for k, v in enumerate(b["vals"]["가동MM"])]
            b["note"] = (b["note"] + " · " if b["note"] else "") + f"{dv_} 직속 인원 제외(직속 행으로 분리)"
    SB.insert(idx, dict(hq=hq_, dv=dv_, tm="", note=f"통계상 {t_}에 포함 → 직속 행으로 분리 (가동대상 = 투입MM)", vals={"가동MM": ext + [0]*(12-len(ext))}))
o = wb.create_sheet("조직별_월별", 2)
o["A1"] = "조직별 월 실적 · 본부 › 사업부 › 팀 (통계 형식)"; o["A1"].font = ft
o["A2"] = "가동대상MM = 26년 가동가득 통계(2-1) 확정값 · 이행/제안/R&D = SOLD투입MM 산출 · 대기 = 가동대상 − 투입 · 가동률 = 투입 ÷ 가동대상 · 가득률 = 이행 ÷ 가동대상"; o["A2"].font = fm
hdr(o, 4, ["본부", "사업부", "팀", "항목"] + [f"{m}월" for m in MON] + [f"1~{LAST}월", "비고"])
ITEMS = ["가동대상MM", "이행", "제안", "R&D·내부과제", "대기", "가동률", "가득률"]
lvfill = {0: PatternFill("solid", fgColor="D5DEEA"), 1: PatternFill("solid", fgColor="EEF2F7"), 2: None}
ncol = 4 + len(MON)
r = 5
def write_block(hq, dv, tm, level, src, note=""):
    """src: dict item -> list of per-month cell formulas/values. returns dict item -> row number"""
    global r
    rows = {}
    for it in ITEMS:
        o.cell(row=r, column=1, value=hq if it == ITEMS[0] else None)
        o.cell(row=r, column=2, value=(dv or "(본부 직속)") if (it == ITEMS[0] and level >= 1) else None)
        o.cell(row=r, column=3, value=(tm or "(직속)") if (it == ITEMS[0] and level >= 2) else None)
        o.cell(row=r, column=4, value=it)
        rows[it] = r
        for k in range(len(MON)):
            col = 5 + k; Lc = L(col)
            if it == "대기": v = f"={Lc}{rows['가동대상MM']}-{Lc}{rows['이행']}-{Lc}{rows['제안']}-{Lc}{rows['R&D·내부과제']}"
            elif it == "가동률": v = f"=IF({Lc}{rows['가동대상MM']}=0,0,({Lc}{rows['이행']}+{Lc}{rows['제안']}+{Lc}{rows['R&D·내부과제']})/{Lc}{rows['가동대상MM']})"
            elif it == "가득률": v = f"=IF({Lc}{rows['가동대상MM']}=0,0,{Lc}{rows['이행']}/{Lc}{rows['가동대상MM']})"
            else: v = src[it][k]
            c = o.cell(row=r, column=col, value=v); c.alignment = C
            c.number_format = "0.00%" if it in ("가동률", "가득률") else NF
        tc = 5 + len(MON)
        if it in ("가동률", "가득률"):
            num = f"({L(tc)}{rows['이행']}+{L(tc)}{rows['제안']}+{L(tc)}{rows['R&D·내부과제']})" if it == "가동률" else f"{L(tc)}{rows['이행']}"
            c = o.cell(row=r, column=tc, value=f"=IF({L(tc)}{rows['가동대상MM']}=0,0,{num}/{L(tc)}{rows['가동대상MM']})"); c.number_format = "0.00%"
        else:
            c = o.cell(row=r, column=tc, value=f"=SUM(E{r}:{L(tc-1)}{r})"); c.number_format = NF
        c.alignment = C
        if it == ITEMS[0] and note: o.cell(row=r, column=tc + 1, value=note).font = fm
        for j in range(1, tc + 1):
            cc = o.cell(row=r, column=j); cc.border = box
            cc.font = fb if (level < 2 or it in ("가동률", "가득률")) else f0
            if lvfill[level] is not None: cc.fill = lvfill[level]
            if it in ("가동률", "가득률") and level == 2: cc.fill = PatternFill("solid", fgColor="F6F8FC")
        r += 1
    return rows
def team_src(blk):
    crit_t = (f'{R("A")},"{blk["hq"]}",{R("C")},"{blk["tm"]}"' if blk["tm"] else f'{R("A")},"{blk["hq"]}",{R("B")},"{blk["dv"] or "(직속)"}",{R("C")},"(직속)"')
    if not blk["dv"] and not blk["tm"]: crit_t = f'{R("A")},"{blk["hq"]}",{R("B")},"(직속)",{R("C")},"(직속)"'
    src = {"가동대상MM": [round(v, 4) for v in blk["vals"]["가동MM"][:len(MON)]]}
    for kd in KINDS: src[kd] = [f'=SUMIFS({R(COLM[mo])},{crit_t},{R("K")},"{kd}")' for mo in MON]
    return src
def sum_src(child_rows):
    src = {}
    for it in ["가동대상MM"] + KINDS:
        src[it] = ["=" + "+".join(f"{L(5+k)}{cr[it]}" for cr in child_rows) if child_rows else 0 for k in range(len(MON))]
    return src
order_hq = HQS + [h for h in dict.fromkeys(b["hq"] for b in SB) if h not in HQS]
grand = []
for hq in order_hq:
    blks = [b for b in SB if b["hq"] == hq]
    if not blks: continue
    # 본부 소계 자리 확보 후 하위 작성 → 소계는 하위 행 참조 (위에 두기 위해 먼저 placeholder)
    hq_start = r; r += len(ITEMS)
    hq_children = []
    for dv in dict.fromkeys(b["dv"] for b in blks):
        dblks = [b for b in blks if b["dv"] == dv]
        if dv:
            dv_start = r; r += len(ITEMS)
            kids = [write_block(hq, dv, b["tm"], 2, team_src(b), b["note"]) for b in dblks]
            save = r; r = dv_start; dr = write_block(hq, dv, "", 1, sum_src(kids)); r = save
            hq_children.append(dr)
        else:
            for b in dblks: hq_children.append(write_block(hq, "", b["tm"], 2, team_src(b), b["note"]))
    save = r; r = hq_start; hr_ = write_block(hq, "", "", 0, sum_src(hq_children)); r = save
    grand.append(hr_)
# 전체
tr_ = write_block("아이티센클로잇 합계", "", "", 0, sum_src(grand))
o.freeze_panes = "E5"; autofit(o); o.column_dimensions["A"].width = 18; o.column_dimensions["B"].width = 26; o.column_dimensions["C"].width = 22; o.column_dimensions[L(6+len(MON))].width = 60

# 5) 제외·재분류
e = wb.create_sheet("제외·재분류")
e["A1"] = "제외 및 재분류 내역"; e["A1"].font = ft
hdr(e, 3, ["처리", "사유", "조직", "성명", "정규직/계약직", "PJT 코드", "PJT 명", "시스템구분", "적용 구분", f"1~{LAST}월 MM"])
r = 4
rows = [("제외", rr["제외사유"], rr) for _, rr in ex.iterrows()] + \
       [("재분류", rr["분류근거"] or "코드 끝자리 기준", rr) for _, rr in use[use["재분류"] | (use["분류근거"] != "")].iterrows()]
for kind, why, rr in rows:
    vals = [kind, why, rr["조직"], rr["성명"], rr["정규직/계약직"], rr["코드"], rr["PJT 명"], rr["시스템구분"], rr["구분"] if kind == "재분류" else "", round(float(sum(rr[c] for c in MC)), 4)]
    for j, v in enumerate(vals, 1):
        c = e.cell(row=r, column=j, value=v if not (isinstance(v, float) and pd.isna(v)) else None); c.font = f0; c.border = box
    e.cell(row=r, column=10).number_format = NF; e.cell(row=r, column=10).alignment = C
    e.cell(row=r, column=1).font = Font(name=FN, size=10, bold=True, color="A2551B" if kind == "제외" else "3B597A")
    r += 1
e.freeze_panes = "C4"; e.auto_filter.ref = f"A3:J{r-1}"; autofit(e); e.column_dimensions["G"].width = 46; e.column_dimensions["C"].width = 36

# 6) 산출기준
k = wb.create_sheet("산출기준")
k["A1"] = "산출 기준"; k["A1"].font = ft
rules = [
 ("원본", "SOLD투입MM목록_20261002 (사내 시스템 다운로드) · 1행 = 1인 × 1프로젝트, 월별 MM"),
 ("실적 구간", f"1~{LAST}월. 'Activity 실적(누적, MM)' = 1~{LAST}월 합계로 전 행 일치 확인. {LAST+1}월 이후는 계획값이라 제외"),
 ("법인", "아이티센클로잇만. 조직이 'ITC-JAPAN_'으로 시작하는 행(아이티센재팬) 제외"),
 ("인원", "정규직/계약직 = '계약직(일반)' 제외 · '계약직(촉탁)'·정규직·임원 포함"),
 ("구분", "PJT 코드 끝자리: C·W = 이행(무상유지보수 포함) / P = 제안 / I·N = R&D·내부과제"),
 ("예외", "사업유형 '비매출' → R&D·내부과제 · ('동행복권 Next Gen → R&D' 규칙은 아이티센엔텍 전용 — 클로잇 실적에는 적용하지 않음)"),
 ("직속", "사업부 직속 인원은 직속 행으로 따로 표시. 통계에는 해당 사업부 첫 팀에 포함되어 있어, 직속 행 가동대상 = 직속 인원 투입MM으로 두고 그만큼 그 팀 가동대상에서 뺌"),
 ("이관", "CSO_AI이노베이션센터(현재 타 법인 전적) 실적은 AX사업본부 › AX Consulting & Eng 사업부 › AX엔지니어링팀으로 이관. R&D는 이행으로 처리, 제안(P)은 제안 유지"),
 ("관리법인", "AX엔지니어링팀(공공) = 인사정보상 관리법인 SS → 아이티센클로잇 통계에서 제외 (26년 가동가득 통계와 동일)"),
 ("조직", "조직명을 본부 › 사업부 › 팀으로 분리 (중복 접두어 정리 · 사업부/팀이 없으면 '직속')"),
 ("표시", "수치는 소수점 둘째 자리 · 열 너비는 내용에 맞춤"),
]
for i, (a, b) in enumerate(rules, 3):
    k.cell(row=i, column=1, value=a).font = fb; k.cell(row=i, column=2, value=b).font = f0
k.column_dimensions["A"].width = 12; k.column_dimensions["B"].width = 110

# 7) 통계 대조 (26년 가동가득 통계_261002 · 2-1 시트)
st = pd.read_pickle(__import__('cfg').w("stats21.pkl"))
SMK = [f"m{m}" for m in MON]
NM = {"스포츠Tech사업부 소계": "스포츠Tech사업부", "DX사업본부 소계": "DX사업본부", "AX 사업본부 소계": "AX사업본부", "ENT사업본부별 소계": "ENT사업본부", "DS사업본부 소계": "DS사업본부"}
KM = {"Sold": "이행", "제안": "제안", "R&D/과제": "R&D·내부과제"}
seen = set(); stat = {}
for _, rr in st.iterrows():
    if rr["dv"] in NM and rr["k"] in KM:
        key = (NM[rr["dv"]], KM[rr["k"]])
        if key in seen:  # 두 번째 'DS사업본부 소계' 블록 = 전체 합계
            key = ("합계", KM[rr["k"]])
        seen.add(key); stat[key] = [float(rr[c]) if c in rr.index else None for c in SMK]
cmpw = wb.create_sheet("통계 대조")
cmpw["A1"] = "26년 가동가득 통계(2-1 조직별 월별) 대조 · 아이티센클로잇"; cmpw["A1"].font = ft
cmpw["A2"] = "통계값은 '26년 가동가득 통계_261002.xlsx' 2-1 시트에서 옮겨온 값 · 차이 = 산출 − 통계 (0이면 일치)"; cmpw["A2"].font = fm
hdr(cmpw, 4, ["본부", "구분", "항목"] + [f"{m}월" for m in MON] + [f"1~{LAST}월"])
r = 5
red = Font(name=FN, size=10, bold=True, color="D32F2F")
for hq in HQS + ["합계"]:
    for kd in KINDS:
        tv = stat.get((hq, kd))
        if tv is None: continue
        base = r
        for lab in ("산출", "통계", "차이"):
            cmpw.cell(row=r, column=1, value=hq if lab == "산출" and kd == KINDS[0] else None).font = fb
            cmpw.cell(row=r, column=2, value=kd if lab == "산출" else None).font = f0
            cmpw.cell(row=r, column=3, value=lab).font = fb if lab == "차이" else f0
            for k, mo in enumerate(MON):
                col = 4 + k
                if lab == "산출":
                    f = (f'=SUMIFS({R(COLM[mo])},{R("A")},"{hq}",{R("K")},"{kd}")' if hq != "합계" else f'=SUMIFS({R(COLM[mo])},{R("K")},"{kd}")')
                elif lab == "통계": f = round(tv[k], 4) if k < len(tv) and tv[k] is not None else None
                else: f = f"=ROUND({L(col)}{base}-{L(col)}{base+1},2)"
                c = cmpw.cell(row=r, column=col, value=f); c.number_format = NF; c.alignment = C; c.border = box
            c = cmpw.cell(row=r, column=4 + len(MON), value=f"=SUM(D{r}:{L(3+len(MON))}{r})"); c.number_format = NF; c.alignment = C; c.border = box; c.font = fb
            for j in (1, 2, 3): cmpw.cell(row=r, column=j).border = box
            if lab == "차이":
                for j in range(1, 5 + len(MON)): cmpw.cell(row=r, column=j).fill = sub
            r += 1
from openpyxl.formatting.rule import CellIsRule
cmpw.conditional_formatting.add(f"D5:{L(4+len(MON))}{r}", CellIsRule(operator="notBetween", formula=["-0.005", "0.005"], font=red))
cmpw.freeze_panes = "D5"; autofit(cmpw); cmpw.column_dimensions["A"].width = 18

for ws in wb.worksheets:
    ws.sheet_view.showGridLines = False
wb.active = 0
wb.save(OUT)
print("use", len(use), "ex", len(ex), ex["제외사유"].value_counts().to_dict(), "reclass", int((use["재분류"] | (use["분류근거"] != "")).sum()))
print(f"{LAST}월", round(use[f"2026년_{LAST}월"].sum(), 2), use.groupby("구분")[f"2026년_{LAST}월"].sum().round(2).to_dict())
use.to_pickle(__import__('cfg').w("use_clo.pkl"))
