"""입력 파일 '자리(role)' 정의와 업로드 → 자리 연결 규칙

규칙 (사용자 확정)
- 1~9월 실적 = SOLD투입MM목록 (클로잇·엔텍 각각)
- 10~12월 = 투입계획. 부서 파일이 하반기 총괄보다 우선, 하반기 총괄은 가장 최근 것
- 가동가득 통계 파일이 올라와 있으면 조직 숫자와 대기 명단을 그 파일 기준으로 맞춤 (최종 기준)
"""
import os, warnings
warnings.filterwarnings("ignore")

ROLES = {
    # role: (이름, 설명)
    "sold_clo": ("SOLD투입MM목록 · 아이티센클로잇", "1~9월 실적 · 아이티센클로잇"),
    "sold_et": ("SOLD투입MM목록 · 아이티센엔텍", "1~9월 실적 · 아이티센엔텍 (ENT사업본부)"),
    "target_clo": ("가동인력목록 · 아이티센클로잇", "아이티센클로잇 가동대상 (AX 외)"),
    "target_et": ("가동인력목록 · 아이티센엔텍", "아이티센엔텍 가동대상"),
    "hr": ("통합인사정보조회", "AX사업본부 가동대상 · 직급·직무"),
    "stats_base": ("가동가득 통계 (조직 구조)", "조직 구조 · 확정 가동대상MM"),
    "stats": ("가동가득 통계 (최종 기준)", "<b>최종 기준</b> · 조직별 가동MM·이행·제안·R&amp;D·대기 + 대기 명단"),
    "cp": ("프로젝트 코드 목록 (CP)", "프로젝트 현황"),
    "plan_hb": ("투입계획 · 하반기 총괄", "10~12월 투입계획 · 부서 파일이 없는 아이티센클로잇 부서"),
    "plan_hb2": ("투입계획 · 하반기 총괄 (최신)", "10~12월 투입계획 · MSP·플랫폼엔지니어링팀 · DS사업본부"),
    "plan_ec": ("투입계획 · EC1·EC2사업부", "10~12월 투입계획 · EC1·EC2사업부 (우선)"),
    "plan_es": ("투입계획 · 클로잇 ES사업부", "10~12월 투입계획 · ES사업부 (우선)"),
    "plan_ax": ("투입계획 · AX사업본부", "10~12월 투입계획 · AX사업본부 (우선)"),
    "plan_ees": ("투입계획 · 엔텍 ES사업부", "10~12월 투입계획 · 엔텍 ES사업부"),
    "plan_eem": ("투입계획 · 엔텍 EM사업부", "10~12월 투입계획 · 엔텍 EM사업부"),
    "plan_msp": ("투입계획 · MSP 독자양식", "비교용"),
    "plan_dxp": ("투입계획 · 플랫폼 독자양식", "비교용"),
}
SHORT_NAME = {"plan_hb": "하반기", "plan_hb2": "하반기", "plan_ec": "EC1·2사업부", "plan_es": "ES사업부", "plan_ax": "AX",
              "plan_ees": "엔텍 ES", "plan_eem": "엔텍 EM", "plan_msp": "MSP 독자양식", "plan_dxp": "플랫폼 독자양식"}
PLAN_FMT = {"plan_ax": "ax", "plan_msp": "msp", "plan_dxp": "platform"}   # 나머지 plan_* 는 rolling(인력롤링 양식)

CLO, ET = "아이티센클로잇", "아이티센엔텍"
HB_DEPT = "전체 (하반기 총괄)"

def split_dept(dept):
    p = [x.strip() for x in (dept or "").split("·")]
    return (p + ["", "", "", ""])[:4]   # corp, hq, dv, tm

def _detect_format_raw(path):
    """투입계획 양식 판별: ax / platform / msp / rolling / None"""
    import openpyxl
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return None
    try:
        names = [s.strip() for s in wb.sheetnames]
        if "AX사업본부" in names: return "ax"
        if "Platform" in names: return "dx" if "MSP" in names else "platform"   # DX 인력운용 현황: MSP·Platform 시트
        if any(n.endswith("인력_투입현황MM") for n in names): return "rolling"
        ws = wb.worksheets[0]
        for r in ws.iter_rows(max_row=4, values_only=True):
            if any(isinstance(c, str) and "MSP" in c and "투입 계획" in c for c in r): return "msp"
        return None
    finally:
        try: wb.close()   # Windows: 닫지 않으면 파일을 지울 수 없음
        except Exception: pass

_FMT_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fmtcache.json")

def detect_format(path):
    """양식 판별 결과를 (경로·수정시각·크기) 기준으로 저장해 두고 재사용 — 큰 엑셀을 매번 열지 않게 함"""
    import json
    try:
        st = os.stat(path); key = f"{os.path.abspath(path)}|{st.st_mtime_ns}|{st.st_size}"
    except OSError:
        return _detect_format_raw(path)
    try:
        with open(_FMT_CACHE, encoding="utf-8") as f: c = json.load(f)
    except Exception:
        c = {}
    if key in c: return c[key]
    r = _detect_format_raw(path)
    c = {k: v for k, v in c.items() if k.split("|")[0] != os.path.abspath(path)}
    c[key] = r
    try:
        with open(_FMT_CACHE, "w", encoding="utf-8") as f: json.dump(c, f, ensure_ascii=False)
    except Exception:
        pass
    return r

def infer_dept(name, fmt):
    """부서를 고르지 않고 올린 투입계획 → 파일 이름·양식으로 부서 추정 (모르면 None)"""
    n = (name or "").replace(" ", "")
    ent = any(k in n for k in ("엔텍", "ET사업본부", "엔터사업본부"))
    if fmt == "ax": return f"{CLO} · AX사업본부"
    if fmt in ("dx", "platform", "msp"): return f"{CLO} · DX사업본부 · DX-Eng사업부"
    if fmt != "rolling": return None
    if "하반기" in n: return HB_DEPT
    if ent and "EM" in n: return f"{ET} · ENT사업본부 · EM사업부"
    if ent and "ES" in n: return f"{ET} · ENT사업본부 · ES사업부"
    if "EC1" in n or "EC2" in n: return f"{CLO} · ENT사업본부 · EC1사업부"
    if "ES사업부" in n: return f"{CLO} · ENT사업본부 · ES사업부"
    for k, d in (("DS", f"{CLO} · DS사업본부"), ("스포츠", f"{CLO} · 스포츠Tech사업부"), ("삼성BC", f"{CLO} · ENT사업본부 · 삼성BC사업부")):
        if k in n: return d
    return None

def role_for_upload(kind, dept, fmt=None):
    """업로드 1건 → (role 또는 None, dept_scope 또는 None, 오류)"""
    corp, hq, dv, tm = split_dept(dept)
    if kind in ("sold", "target"):
        if corp not in (CLO, ET): return None, None, "SOLD·가동인력목록은 법인(아이티센클로잇/아이티센엔텍)을 골라야 합니다."
        return f"{kind}_{'clo' if corp == CLO else 'et'}", None, None
    if kind in ("hr", "cp"): return kind, None, None
    if kind == "stats": return "stats", None, None
    if kind != "plan": return None, None, "알 수 없는 종류입니다."
    if fmt is None: return None, None, "투입계획 양식을 알아볼 수 없습니다. (인력롤링 양식 · AX 가득가동현황 · DX 인력운용 현황 · MSP 투입계획 중 하나여야 합니다. 시트 이름이 바뀌었는지 확인해 주세요)"
    if not corp: return None, None, "부서를 알 수 없습니다. 업로드할 때 부서를 골라 주세요."
    if dept == HB_DEPT or (not hq and corp == CLO and fmt == "rolling"):
        return ("plan_hb" if fmt == "rolling" else None), None, (None if fmt == "rolling" else "하반기 총괄은 인력롤링 양식이어야 합니다.")
    if tm and fmt == "rolling":   # 팀 단위 제출: 그 팀 범위에만 적용 (사업부 파일·하반기보다 우선)
        return None, dict(corp=corp, hq=hq, dv=dv, tm=tm), None
    if corp == ET:
        if fmt != "rolling": return None, None, "엔텍 투입계획은 인력롤링 양식이어야 합니다."
        return ("plan_ees" if dv == "ES사업부" else "plan_eem"), None, None
    if hq == "AX사업본부":
        if fmt == "ax": return "plan_ax", None, None
    if dv in ("EC1사업부", "EC2사업부") and fmt == "rolling": return "plan_ec", None, None
    if hq == "ENT사업본부" and dv == "ES사업부" and fmt == "rolling": return "plan_es", None, None
    # 그 밖의 부서: 그 부서 범위에만 적용 (하반기보다 우선)
    scope = dict(corp=corp, hq=hq, dv=dv, tm="")
    if fmt == "dx": scope.update(hq="DX사업본부", dv="DX-Eng사업부", tm="")
    elif fmt == "platform": scope.update(hq="DX사업본부", dv="DX-Eng사업부", tm="플랫폼엔지니어링팀")
    elif fmt == "msp": scope.update(hq="DX사업본부", dv="DX-Eng사업부", tm="MSP엔지니어링팀")
    elif fmt == "ax": return None, None, "AX 가득가동현황 양식은 AX사업본부만 올릴 수 있습니다."
    return None, scope, None
