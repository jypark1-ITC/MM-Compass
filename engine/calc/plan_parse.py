import openpyxl, pandas as pd, warnings, collections
warnings.filterwarnings("ignore")
D = ""
def parse_mm(f, sheet=None):
    wb = openpyxl.load_workbook(f if __import__('os').path.isabs(f) else D + f, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else next(w for w in wb.worksheets if w.title.strip().endswith("인력_투입현황MM"))
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:15]) if r and "성명" in [str(x).strip() if x else "" for x in r] and any(str(x).strip() == "1월" for x in r if x))
    H = [str(x).strip() if x is not None else "" for x in rows[hi]]
    def col(name):
        return H.index(name) if name in H else None
    mcols = [H.index(f"{m}월") for m in range(1, 13)]
    out = []
    for r in rows[hi+1:]:
        if not r or all(x is None for x in r): continue
        g = lambda n: r[col(n)] if col(n) is not None and col(n) < len(r) else None
        rec = dict(사번=g("사번"), 성명=g("성명"), 직위=g("직위"), 부서=g("부서"), 팀=g("팀"), 상태=g("투입/미투입"), PJT=g("프로젝트명"),
                   코드=g("프로젝트코드"), 구분=g("제안/이행"), win=g("win/Loss"))
        mm = []
        for c in mcols:
            v = r[c] if c < len(r) else None
            try: mm.append(float(v) if v not in (None, "") else 0.0)
            except Exception: mm.append(0.0)
        rec["mm"] = mm
        out.append(rec)
    return pd.DataFrame(out), H
if __name__ == "__main__":
    import sys
    for f in ["(261006) 26년 인력롤링_하반기.xlsx", "(261009)26년 인력롤링_EC1 2사업부.xlsx", "(261002)26년 인력롤링_ES사업부.xlsx",
              "(2609)26년 인력운영_ET사업본부_ES사업부_검토완료.xlsx", "(260915)26년 인력롤링_엔텍엔터사업본부_EM사업부.xlsx"]:
        df, H = parse_mm(f)
        print("=====", f, len(df)); print(H[:20])
        print(df.groupby(["부서", "팀"]).size().to_string())
        print("상태", df["상태"].value_counts(dropna=False).to_dict())
        print("구분", df["구분"].value_counts(dropna=False).to_dict())
