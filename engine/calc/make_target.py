import pandas as pd, warnings, sys, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter as L
warnings.filterwarnings('ignore')
sys.path.insert(0, __import__('cfg').CALC)
from stats_parse import parse_stats
UP = ""
OUT = __import__('cfg').w("report_target.xlsx")
M12 = [f"{m}월" for m in range(1, 13)]

def parse_org(s):
    t = str(s).split("_"); rest = []
    for x in t[1:]:
        if x in ("CLO", "CSO", "ITC-JAPAN", "ET") or x in rest: continue
        rest.append(x)
    hq = rest[0] if rest else ""
    dv = next((x for x in rest[1:] if x.endswith("사업부")), "")
    tm = next((x for x in rest[1:] if not x.endswith("사업부")), "")
    return t[0], hq, dv, tm

rows = []
# ---- 아이티센클로잇 (AX 제외) : 가동인력목록
c = pd.read_excel(__import__('cfg').inp("target_clo"))
po = c["조직"].apply(parse_org)
c["corp"], c["본부"], c["사업부"], c["팀"] = po.str[0], po.str[1], po.str[2], po.str[3]
c["출처"] = "가동인력목록(클로잇)"
c["제외"] = ""
c.loc[c["corp"] == "ITC-JAPAN", "제외"] = "아이티센재팬 제외"
c.loc[(c["제외"] == "") & (c["정규직/계약직"] == "계약직(일반)"), "제외"] = "계약직(일반) 제외"
c.loc[(c["제외"] == "") & (c["본부"] == "AX사업본부"), "제외"] = "AX는 통합인사정보 기준"
ai = c["본부"] == "AI이노베이션센터"
c.loc[ai, "비고"] = "AI이노베이션센터 → AX엔지니어링팀 이관"
c.loc[ai, ["본부", "사업부", "팀"]] = ["AX사업본부", "AX Consulting & Eng 사업부", "AX엔지니어링팀"]
for _, r in c.iterrows():
    rows.append(dict(법인="아이티센클로잇", 본부=r["본부"], 사업부=r["사업부"], 팀=r["팀"], 성명=r["성명"], 그룹사번=str(r["그룹사번"]),
                     입사일=str(r["입사일"])[:10], 구분=r["정규직/계약직"], 재직=r["재직여부"], 출처=r["출처"], 제외=r["제외"], 비고=r.get("비고") if pd.notna(r.get("비고")) else "",
                     **{m: float(r[m]) for m in M12}))
# ---- AX : 통합인사정보 (관리법인 SS 제외)
h = pd.read_excel(__import__('cfg').w("hr.xlsx"), header=None); cols = []
for a, b in zip(h.iloc[0].ffill(), h.iloc[1]): cols.append(f"{a}_{b}" if isinstance(b, str) and b.endswith(("월", "계")) else a)
d = h.iloc[2:].copy(); d.columns = cols
for _, r in d.iterrows():
    ex = ""
    if r["관리법인"] == "SS": ex = "관리법인 SS 제외"
    elif r["가동여부"] != "Y": ex = "가동여부 N"
    elif r["직원구분"] not in ("정규직", "촉탁직", "임원"): ex = f"{r['직원구분']} 제외"
    dv = str(r["사업부"]).split("_")[-1]; tm = str(r["팀"]).split("_")[-1]
    if tm == dv: tm = ""
    rows.append(dict(법인="아이티센클로잇", 본부="AX사업본부", 사업부=dv, 팀=tm, 성명=r["성명"], 그룹사번=str(r["그룹사번"]).zfill(6),
                     입사일=str(r["입사일"])[:10], 구분=r["직원구분"], 재직=r["재직여부"], 출처="통합인사정보(AX) 10.06", 제외=ex, 비고="", **{f"{m}월": float(r[f"주소속_{m}월"]) for m in range(1, 13)}))
# ---- 아이티센엔텍 ENT사업본부 : 가동인력목록_ET
e = pd.read_excel(__import__('cfg').inp("target_et"))
e = e[e["조직"].astype(str).str.startswith("ET_ENT")]
for _, r in e.iterrows():
    p = str(r["조직"]).split("_")
    rows.append(dict(법인="아이티센엔텍", 본부="ENT사업본부", 사업부=p[2] if len(p) > 2 else "", 팀=p[3] if len(p) > 3 else "", 성명=r["성명"],
                     그룹사번=str(r["그룹사번"]), 입사일=str(r["입사일"])[:10], 구분=r["정규직/계약직"], 재직=r["재직여부"], 출처="가동인력목록(엔텍)",
                     제외="계약직(일반) 제외" if r["정규직/계약직"] == "계약직(일반)" else "", 비고="", **{m: float(r[m]) for m in M12}))
df = pd.DataFrame(rows)
# ---- 사이트에서 입력한 인사 변동 (입사·퇴사·휴직·복직·조직이동) → 가동대상MM 반영
import json as _json, hr_apply as _hra
_cfg = __import__('cfg'); HR_RES = []
if _cfg.HR_NOTES:
    df, HR_RES = _hra.apply(df, _cfg.HR_NOTES, int(_cfg.WEEK["label"][:4]))
_json.dump(HR_RES, open(_cfg.w("hr_applied.json"), "w", encoding="utf-8"), ensure_ascii=False)
# 9/14 입사자: 9월 가동대상에서 제외 (10월부터 가동대상)
J914 = df["입사일"] == "2026-09-14"
df.loc[J914, "9월"] = 0.0
df.loc[J914, "비고"] = (df.loc[J914, "비고"].fillna("") + " 9/14 입사 → 9월 가동대상 제외").str.strip()
use = df[df["제외"] == ""].copy()
use.loc[use["사업부"] == "", "사업부"] = "(직속)"; use.loc[use["팀"] == "", "팀"] = "(직속)"

# ---- workbook
FN = "맑은 고딕"; f0 = Font(name=FN, size=10); fb = Font(name=FN, size=10, bold=True); fh = Font(name=FN, size=10, bold=True, color="FFFFFF")
ft = Font(name=FN, size=14, bold=True, color="0F2942"); fm = Font(name=FN, size=9, color="6B7280"); red = Font(name=FN, size=10, bold=True, color="D32F2F")
navy = PatternFill("solid", fgColor="3D5D84"); l0 = PatternFill("solid", fgColor="D5DEEA"); l1 = PatternFill("solid", fgColor="EEF2F7"); tot = PatternFill("solid", fgColor="C9D6E5")
thin = Side(style="thin", color="D0D7E0"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
C = Alignment(horizontal="center", vertical="center", wrap_text=True); NF = "0.00"
wb = openpyxl.Workbook()
def hdr(ws, r, names):
    for i, n in enumerate(names, 1):
        x = ws.cell(row=r, column=i, value=n); x.font = fh; x.fill = navy; x.alignment = C; x.border = box
def autofit(ws, maxw=50):
    w = {}
    for row in ws.iter_rows():
        for x in row:
            if x.value is None: continue
            v = str(x.value); v = "0000.00" if v.startswith("=") else v
            w[x.column_letter] = max(w.get(x.column_letter, 0), sum(2 if ord(ch) > 127 else 1 for ch in v) + 2)
    for k, v in w.items(): ws.column_dimensions[k].width = max(6, min(maxw, v))

# 명단 (가공)
g = wb.active; g.title = "명단"
GC = ["법인", "본부", "사업부", "팀", "성명", "그룹사번", "구분", "재직", "출처", "비고"] + M12 + ["합계"]
hdr(g, 1, GC)
for i, (_, r) in enumerate(use.iterrows(), 2):
    for j, k in enumerate(GC[:10], 1): g.cell(row=i, column=j, value=r[k]).font = f0
    for k, m in enumerate(M12):
        x = g.cell(row=i, column=11 + k, value=round(r[m], 4)); x.number_format = NF; x.alignment = C
    x = g.cell(row=i, column=23, value=f"=SUM(K{i}:V{i})"); x.number_format = NF; x.font = fb; x.alignment = C
NG = len(use) + 1
g.freeze_panes = "F2"; g.auto_filter.ref = f"A1:W{NG}"; autofit(g)
R = lambda col: f"명단!${col}$2:${col}${NG}"

# 조직별 (법인 > 본부 > 사업부 > 팀)
o = wb.create_sheet("조직별_월별", 0)
_A = __import__("cfg").ACTM; _CI = __import__("cfg").CI
o["A1"] = f"2026년 가동대상MM · 조직별 (1~{_A}월 실적 / {_A+1}~12월 예상)"; o["A1"].font = ft
o["A2"] = "클로잇: 가동인력목록(AX 제외) + AX는 통합인사정보(관리법인 SS 제외) · AI이노베이션센터 → AX엔지니어링팀 · 엔텍: ENT사업본부만 · 계약직(일반)·아이티센재팬 제외"; o["A2"].font = fm
hdr(o, 4, ["법인", "본부", "사업부", "팀"] + M12 + [f"1~{_A}월", "연간"])
r = 5
def line(vals_crit, label, level):
    global r
    corp, hq, dv, tm = label
    o.cell(row=r, column=1, value=corp); o.cell(row=r, column=2, value=hq); o.cell(row=r, column=3, value=dv); o.cell(row=r, column=4, value=tm)
    for k, m in enumerate(M12):
        col = L(11 + k)
        f = "=SUMIFS(" + R(col) + "," + ",".join(f'{R(a)},"{b}"' for a, b in vals_crit) + ")"
        x = o.cell(row=r, column=5 + k, value=f); x.number_format = NF; x.alignment = C
        if k >= _A: x.fill = PatternFill("solid", fgColor="F1F4F8")
        if k == _CI: x.font = Font(name=FN, size=10, bold=True, color="0F2942")
    x = o.cell(row=r, column=17, value=f"=SUM(E{r}:{L(4+_A)}{r})"); x.number_format = NF; x.alignment = C; x.font = fb
    x = o.cell(row=r, column=18, value=f"=SUM(E{r}:P{r})"); x.number_format = NF; x.alignment = C; x.font = fb
    for j in range(1, 19):
        x = o.cell(row=r, column=j); x.border = box
        if level < 3: x.font = fb
        if level == 0: x.fill = tot
        elif level == 1: x.fill = l0
        elif level == 2 and j <= 4: x.fill = l1
    r += 1
ORDER = {"ENT사업본부": 0, "DX사업본부": 1, "AX사업본부": 2, "스포츠Tech사업부": 3, "DS사업본부": 4}
for corp in ["아이티센클로잇", "아이티센엔텍"]:
    u = use[use["법인"] == corp]
    line([("A", corp)], (corp, "", "", ""), 0)
    for hq in sorted(u["본부"].unique(), key=lambda x: ORDER.get(x, 9)):
        uh = u[u["본부"] == hq]
        line([("A", corp), ("B", hq)], ("", hq, "", ""), 1)
        for dv in sorted(uh["사업부"].unique(), key=lambda x: (x != "(직속)", x)):
            ud = uh[uh["사업부"] == dv]
            if dv != "(직속)": line([("A", corp), ("B", hq), ("C", dv)], ("", "", dv, ""), 2)
            for tm in sorted(ud["팀"].unique(), key=lambda x: (x != "(직속)", x)):
                line([("A", corp), ("B", hq), ("C", dv), ("D", tm)], ("", "", "" if dv != "(직속)" else "(본부 직속)", tm), 3)
o.freeze_panes = "E5"; autofit(o); o.column_dimensions["C"].width = 26

# 통계 대조 (1~실적 확정 월)
s = wb.create_sheet("통계 대조", 1)
s["A1"] = "26년 가동가득 통계(2-1, 2-2) 가동MM과 대조 · 차이 = 산출 − 통계"; s["A1"].font = ft
s["A2"] = "통계는 사업부 직속 인원을 첫 팀에 포함한 경우가 있어(EC2·ES) 팀 단위 차이는 본부 합계로 확인"; s["A2"].font = fm
hdr(s, 4, ["법인", "본부", "항목"] + [f"{m}월" for m in range(1, _A + 1)] + [f"1~{_A}월"])
SB = parse_stats(); E2 = parse_stats("2-2. 통계(엔텍 엔터사업본부)")
stat = {}
for b in SB: stat.setdefault(("아이티센클로잇", b["hq"]), [0]*_A); stat[("아이티센클로잇", b["hq"])] = [a + v for a, v in zip(stat[("아이티센클로잇", b["hq"])], b["vals"]["가동MM"][:_A])]
for b in E2: stat.setdefault(("아이티센엔텍", "ENT사업본부"), [0]*_A); stat[("아이티센엔텍", "ENT사업본부")] = [a + v for a, v in zip(stat[("아이티센엔텍", "ENT사업본부")], b["vals"]["가동MM"][:_A])]
r = 5
for (corp, hq), sv in sorted(stat.items(), key=lambda kv: (kv[0][0] != "아이티센클로잇", ORDER.get(kv[0][1], 9))):
    base = r
    for lab in ("산출", "통계", "차이"):
        s.cell(row=r, column=1, value=corp if lab == "산출" else None); s.cell(row=r, column=2, value=hq if lab == "산출" else None)
        s.cell(row=r, column=3, value=lab).font = fb if lab == "차이" else f0
        for k in range(_A):
            col = L(11 + k)
            if lab == "산출": v = f'=SUMIFS({R(col)},{R("A")},"{corp}",{R("B")},"{hq}")'
            elif lab == "통계": v = round(sv[k], 4)
            else: v = f"=ROUND({L(4+k)}{base}-{L(4+k)}{base+1},2)"
            x = s.cell(row=r, column=4 + k, value=v); x.number_format = NF; x.alignment = C; x.border = box
        x = s.cell(row=r, column=4 + _A, value=f"=SUM(D{r}:{L(3+_A)}{r})"); x.number_format = NF; x.alignment = C; x.border = box; x.font = fb
        for j in (1, 2, 3): s.cell(row=r, column=j).border = box
        if lab == "차이":
            for j in range(1, 5 + _A): s.cell(row=r, column=j).fill = l1
        r += 1
s.conditional_formatting.add(f"D5:{L(4+_A)}{r}", CellIsRule(operator="notBetween", formula=["-0.005", "0.005"], font=red))
autofit(s)

# 제외 내역
x_ = wb.create_sheet("제외")
hdr(x_, 1, ["법인", "조직(본부/사업부/팀)", "성명", "구분", "출처", "제외 사유", "1~12월 MM"])
for i, (_, rr) in enumerate(df[df["제외"] != ""].iterrows(), 2):
    vals = [rr["법인"], " › ".join(v for v in (rr["본부"], rr["사업부"], rr["팀"]) if v), rr["성명"], rr["구분"], rr["출처"], rr["제외"], round(sum(rr[m] for m in M12), 2)]
    for j, v in enumerate(vals, 1): x_.cell(row=i, column=j, value=v).font = f0
    x_.cell(row=i, column=7).number_format = NF
x_.auto_filter.ref = f"A1:G{len(df[df['제외'] != ''])+1}"; autofit(x_)
for ws in wb.worksheets: ws.sheet_view.showGridLines = False
wb.active = 0
wb.save(OUT)
print("use", len(use), "excluded", (df["제외"] != "").sum())
use.to_pickle(__import__('cfg').w("use_target.pkl"))
