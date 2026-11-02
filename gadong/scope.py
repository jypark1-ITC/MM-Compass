"""업로드 담당자의 담당 범위 (부서·사업부·팀 여러 개 가능)
- users.dept  : 대표 부서 (예전 방식 그대로)
- users.depts : 담당 범위 전체 목록(JSON) — 본부·사업부·팀 어느 단계든 가능. 비어 있으면 대표 부서 하나
- ALL("*")    : 내 담당 전체 (여러 팀을 한 번에 다룰 때)
- 화면에서 고른 '지금 작업 중인 범위'는 세션에 기억 (cur_dept)
"""
import json
from flask import session

ALL = "*"

def user_depts(u):
    if not u: return []
    try: L = json.loads(u["depts"] or "[]") if "depts" in u.keys() else []
    except Exception: L = []
    L = [x for x in L if x]
    if u["dept"] and u["dept"] not in L: L = [u["dept"]] + L
    return L

def upload_options(u):
    """업로드 화면에 보여 줄 부서 목록: 내 담당 + 그 아래 사업부 (다른 본부는 안 보임). 담당 설정 자체는 바꾸지 않음"""
    import os
    from . import org
    try: allx = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "depts.json"), encoding="utf-8"))
    except Exception: allx = []
    out = []
    for x in user_depts(u):
        if x not in out: out.append(x)
        for d in allx:
            if d != x and d not in out and org.covers(x, d): out.append(d)
    return out

def units_of(u, dept):
    """화면에서 고른 범위 → 실제 범위 목록 ('*' = 내 담당 전체, 관리자는 두 법인 전체)"""
    if dept == ALL:
        if u["role"] == "admin": return ["아이티센클로잇", "아이티센엔텍"]
        return user_depts(u)
    return [dept] if dept else []

def allowed(u, dept):
    """그 범위가 내 담당 안인지 (담당이 사업부면 그 아래 팀도 포함)"""
    from . import org
    if u is None: return False
    if u["role"] == "admin": return True
    L = user_depts(u)
    if dept == ALL: return bool(L)
    return any(org.covers(x, dept) for x in L)

def pick_dept(u, want=None):
    """담당 범위 중 하나: 요청한 범위(담당이면) → 세션에 기억된 범위 → 첫 범위"""
    L = user_depts(u)
    if want and (want in L or (want == ALL and len(L) > 1) or allowed(u, want)):
        session["cur_dept"] = want; return want
    c = session.get("cur_dept")
    return c if c and (c in L or (c == ALL and len(L) > 1) or allowed(u, c)) else (L[0] if L else "")
