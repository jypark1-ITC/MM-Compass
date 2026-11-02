import pandas as pd
SRC_ST = __import__('cfg').inp("stats_base")
HQM = {"AX 사업본부": "AX사업본부"}
DVM = {"AX 사업부": "AX사업부", "DX 사업부": "DX사업부", "DX Eng 사업부": "DX-Eng사업부", "DS TS사업부": "DS-TS사업부"}
TMM = {"AX Eng팀": "AX엔지니어링팀", "DS Service팀": "DS-Service팀", "DS 전략사업팀": "DS-전략사업팀", "MSP Eng팀": "MSP엔지니어링팀",
       "플랫폼 Eng팀": "플랫폼엔지니어링팀", "Alliance/마케팅팀": "Alliance-Marketing팀", "ENT컨설팅팀": "Ent컨설팅팀"}
def clean(x): return " ".join(str(x).replace("(조직 신설)", "").split()).strip()
def parse_stats(sheet="2-1. 통계(조직별_월별현황)"):
    t = pd.read_excel(SRC_ST, sheet, header=None)
    blocks = []; hq = dv = None; cur = None
    for _, r in t.iterrows():
        if pd.notna(r[1]) and str(r[1]).strip() not in ("CLO", "조직"): hq = clean(r[1])
        if pd.notna(r[2]): dv = clean(r[2])
        k = r[4]
        if k == "가동MM":
            if "소계" in str(dv) or str(hq).startswith("계"): cur = None; continue
            tm = clean(r[3]) if pd.notna(r[3]) else ""
            if hq is None: H, D = dv, ""
            else: H = HQM.get(hq, hq); D = DVM.get(dv, dv)
            T = TMM.get(tm, DVM.get(tm, tm))
            if D == H: D = ""
            if T in (D, H): T = ""
            cur = dict(hq=H, dv=D, tm=T, note=str(r[19]) if pd.notna(r[19]) else "", vals={})
            blocks.append(cur)
        if cur is not None and k in ("가동MM", "제안", "R&D/과제", "Sold", "New", "대기"):
            cur["vals"][k] = [float(r[4+m]) if pd.notna(r[4+m]) else 0.0 for m in range(1, 13)]
    return blocks
if __name__ == "__main__":
    for b in parse_stats(): print(b["hq"], "|", b["dv"], "|", b["tm"], [round(v,2) for v in b["vals"]["가동MM"][:9]])
