import pandas as pd, html, warnings, datetime as dt
warnings.filterwarnings('ignore')
D = __import__('cfg').WORK
E = html.escape
TODAY = pd.Timestamp(__import__("cfg").WEEK.get("thu") or "2026-10-06")   # 그 주 목요일 기준
_CUR = __import__("cfg").CUR; _CI = _CUR - 1
MON = list(range(1, 13))   # 2026년 1~12월

def load_hr():
    h = pd.read_excel(D + "hr.xlsx", header=None); cols = []
    for a, b in zip(h.iloc[0].ffill(), h.iloc[1]):
        cols.append(f"{a}_{b}" if isinstance(b, str) and b.endswith(("월", "계")) else a)
    d = h.iloc[2:].copy(); d.columns = cols
    d["그룹사번"] = d["그룹사번"].astype(str).str.zfill(6)
    for m in range(1, 13): d[f"주소속_{m}월"] = d[f"주소속_{m}월"].astype(float)
    for c in ["적용시작일", "적용종료일", "입사일", "퇴사일", "휴직시작일", "휴직종료일"]: d[c] = pd.to_datetime(d[c], errors="coerce")
    for c in ["사업부", "팀"]: d[c + "_s"] = d[c].astype(str).str.split("_").str[-1]
    d["elig"] = (d["가동여부"] == "Y") & d["직원구분"].isin(["정규직", "촉탁직", "임원"])
    return d

def fd(x): return "" if pd.isna(x) else x.strftime("%Y.%m.%d")

def hr_view_real(ic):
    d = load_hr()
    inc, exc = [], []
    for sid, g in d.groupby("그룹사번"):
        g = g.sort_values("적용시작일"); last = g.iloc[-1]
        mm = [g[g["elig"]][f"주소속_{m}월"].sum() for m in MON]
        teams = list(dict.fromkeys(g["팀_s"]))
        note = []
        if len(teams) > 1: note.append("전배 " + " → ".join(teams))
        lv = g[g["휴직시작일"].notna()]
        leave = f'{fd(lv["휴직시작일"].min())[2:]} ~ {fd(lv["휴직종료일"].max())[2:]}' if len(lv) else ""
        rec = dict(sid=sid, name=last["성명"], div=last["사업부_s"], team=last["팀_s"], typ=last["직원구분"], title=str(last["호칭"]),
                   join=fd(last["입사일"]), quit=fd(last["퇴사일"]), leave=leave, mm=mm, note=" · ".join(note), corp=last["관리법인"], kad=last["가동여부"])
        if sum(mm) > 0:
            inc.append(rec)
        else:
            if (g["직원구분"] == "계약직").all(): r = "계약직"
            elif not g["elig"].any() and (g["가동여부"] == "N").any(): r = "가동여부 N"
            elif pd.notna(last["퇴사일"]) and last["퇴사일"] <= TODAY: r = "퇴사"
            elif last["재직여부"] == "휴직": r = "휴직"
            else: r = "2026년 소속 없음"
            rec["reason"] = r; exc.append(rec)
    inc.sort(key=lambda r: (r["div"], r["team"], r["name"])); exc.sort(key=lambda r: (r["reason"], r["name"]))
    tot = [sum(r["mm"][i] for r in inc) for i in range(12)]
    n_exec = sum(1 for r in inc if r["typ"] == "임원")
    from collections import Counter
    rc = Counter(r["reason"] for r in exc)
    def tr_inc(r):
        cells = "".join(f'<td class="{"zero" if v == 0 else ("part" if v < 0.999 else "")}{" cm" if i == _CI else ""}">{v:.2f}</td>' for i, v in enumerate(r["mm"])) + f'<td class="strong">{sum(r["mm"]):.2f}</td>'
        np = '<span class="pill p-mid">비매출 모수</span>' if r["typ"] == "임원" else ""
        corp = f' <span class="tag-np">{E(str(r["corp"]))}</span>' if r["corp"] != "CN" else ""
        return (f'<tr><td class="l mono">{r["sid"]}</td><td class="l">{E(r["name"])}</td><td class="l">{E(r["div"])}</td><td class="l">{E(r["team"])}{corp}</td>'
                f'<td class="l">{E(r["typ"])} {np}</td><td class="l">{E(r["title"])}</td><td class="c">{r["join"]}</td><td class="c">{r["quit"] or "—"}</td>'
                f'<td class="c">{r["leave"] or "—"}</td>{cells}<td class="l muted">{E(r["note"])}</td></tr>')
    def tr_exc(r):
        return (f'<tr><td class="l mono">{r["sid"]}</td><td class="l">{E(r["name"])}</td><td class="l">{E(r["div"])}</td><td class="l">{E(r["team"])}</td>'
                f'<td class="l">{E(r["typ"])}</td><td class="c">{r["kad"]}</td><td class="c">{r["quit"] or "—"}</td><td class="c">{r["leave"] or "—"}</td>'
                f'<td class="c"><span class="pill p-warn">{E(r["reason"])}</span></td></tr>')
    TH_M = "".join(f'<th{" class=cm" if m == _CUR else ""}>{m}월</th>' for m in MON)
    TF_M = "".join(f'<td>{v:.2f}</td>' for v in tot)
    chips = "".join(f'<span class="hrc"><b>{v}</b>{k}</span>' for k, v in rc.most_common())
    return f'''
<div class="view" id="v-hr">
  <div class="titlebar"><h1>인사정보</h1><span class="chip solid">AX사업본부</span><span class="chip">통합인사정보조회 · 2026.10.06</span>
    <div class="meta2">실제 데이터 · 인원 {len(inc)+len(exc)}명 (발령 {len(d)}건)</div></div>
  <div class="src-grid" id="h1">
    <section class="card-sec src on"><div class="sec-head"><h2>① 인사정보 파일 업로드</h2><span class="pill p-ok">사용 중</span></div>
      <p>통합인사정보조회에서 내려받은 파일(.xls)을 그대로 올리면 발령 기간별 <b>주소속 월별 값</b>으로 가동대상MM을 계산하고, 직전 파일과 비교해 입사·퇴사·휴직·전적·전배를 찾아냅니다.</p>
      <div class="row"><button class="tbtn">파일 선택</button><span class="muted">최종 반영 10.06 10:07 · 통합인사정보조회_20261006100738.xls · 직전 대비 변경 2명 (남지호·이충헌 AX Consulting &amp; Eng 사업부 → AI서비스팀)</span></div></section>
    <section class="card-sec src"><div class="sec-head"><h2>② 사내 인사시스템 연동</h2><span class="pill p-mid">검토 중</span></div>
      <p>IT팀에서 DB 조회 또는 API 제공이 가능하면 매일 자동으로 가져옵니다. 엔텍은 조회 권한이 없으므로 당분간 롤링파일의 「직군_직무_현황」 시트(같은 양식)로 대체합니다.</p>
      <div class="row"><span class="muted">확인 필요: 연동 방식(DB/API) · 조회 권한 · 갱신 주기</span></div></section>
  </div>
  <section class="card-sec" id="h2">
    <div class="sec-head"><h2>가동대상MM 계산 규칙</h2></div>
    <div class="rule num">가동대상MM = 「주소속」 월별 값 합계 (재직 영업일 ÷ 전체 영업일 · 휴직 기간 0 · 발령 기간별 행 합산)
      <span class="ex">대상: 가동여부 <b>Y</b> · 직원구분 <b>정규직 · 촉탁직 · 임원</b> (계약직 제외) · 임원은 <b>비매출 모수</b>로 별도 집계</span></div>
    <div class="kpis num k4" style="margin-top:14px">
      <div class="kpi"><div class="label">가동대상 인원</div><div class="value">{len(inc)}<small>명</small></div><div class="ytd">2026년 중 1개월 이상 대상</div></div>
      <div class="kpi"><div class="label">가동대상 MM</div><div class="value">{tot[_CI]:.2f}<small>{_CUR}월(당월)</small></div><div class="ytd">2026년 합계 {sum(tot):.2f}{f" · 1~{_CI}월 {sum(tot[:_CI]):.2f}" if _CI else ""}{"".join(f" · {m + 1}월 {tot[m]:.2f}" for m in range(_CUR, 12))}</div></div>
      <div class="kpi alt"><div class="label">비매출 모수<i>임원</i></div><div class="value">{n_exec}<small>명</small></div><div class="ytd">가동대상에 포함 · 비매출 제외 가득률 분모에서 제외</div></div>
      <div class="kpi"><div class="label">제외 인원</div><div class="value">{len(exc)}<small>명</small></div><div class="ytd">아래 「제외 인원」 탭에서 사유 확인</div></div>
    </div>
  </section>
  <section class="card-sec" id="h3">
    <div class="sec-head"><h2>인원별 가동대상MM</h2><span class="sub">1 미만 = 일할 계산된 달 · 회색 0 = 그 달 대상 아님</span></div>
    <div class="tabs" role="tablist" id="hrtabs">
      <button role="tab" aria-selected="true" data-t="hr-inc">가동대상 ({len(inc)})</button>
      <button role="tab" aria-selected="false" data-t="hr-exc">제외 인원 ({len(exc)})</button>
      <span class="tools"><input class="tfilter" data-target="hr-inc,hr-exc" placeholder="이름 · 팀 · 사번 필터"></span>
    </div>
    <div class="hr-sum num" id="hr-exc-sum" style="display:none">{chips}</div>
    <div class="scroll" data-search id="hr-inc"><table>
      <thead><tr><th class="l">그룹사번</th><th class="l">성명</th><th class="l">사업부</th><th class="l">팀</th><th class="l">직원구분</th><th class="l">호칭</th><th class="c">입사일</th><th class="c">퇴사일</th><th class="c">휴직</th>{TH_M}<th>연간</th><th class="l">비고</th></tr></thead>
      <tbody>{"".join(tr_inc(r) for r in inc)}</tbody>
      <tfoot><tr><td class="l" colspan="9">합계 {len(inc)}명</td>{TF_M}<td>{sum(tot):.2f}</td><td></td></tr></tfoot></table></div>
    <div class="scroll" data-search id="hr-exc" style="display:none"><table>
      <thead><tr><th class="l">그룹사번</th><th class="l">성명</th><th class="l">사업부</th><th class="l">팀</th><th class="l">직원구분</th><th class="c">가동여부</th><th class="c">퇴사일</th><th class="c">휴직</th><th class="c">제외 사유</th></tr></thead>
      <tbody>{"".join(tr_exc(r) for r in exc)}</tbody></table></div>
  </section>
</div>
'''

def proj_view_real(ic):
    c = pd.read_excel(__import__('cfg').inp("cp"), header=1)
    c = c[c["사업단계"] != "실주"].copy()
    c["부서"] = c["사업부서"].astype(str).str.replace("CLO_", "", regex=False)
    c["본부"] = c["부서"].str.split("_").str[0]
    c["ax"] = c["본부"].str.contains("AX")
    c = c.sort_values(["ax", "사업코드"], ascending=[False, False])
    stage_kind = {"이행": "ex", "무상유지보수": "ex"}
    def kind(r):
        if r["사업유형"] == "비매출": return "rd"
        return stage_kind.get(r["사업단계"], "pr")
    c["k"] = c.apply(kind, axis=1)
    lab = {"ex": ("이행 단계", "k-ex"), "pr": ("영업 단계", "k-pr"), "rd": ("비매출", "k-rd")}
    def d8(x):
        x = pd.to_datetime(x, errors="coerce"); return "" if pd.isna(x) else x.strftime("%y.%m")
    trs = []
    for _, r in c.iterrows():
        l, kc = lab[r["k"]]
        trs.append(f'<tr data-kind="{r["k"]}" data-ax="{1 if r["ax"] else 0}"><td class="l mono">{E(str(r["사업코드"]))}</td><td class="l wrap">{E(str(r["사업명"]))}</td>'
                   f'<td class="c"><span class="kind {kc}">{l}</span></td><td class="l">{E(str(r["사업단계"]))}</td><td class="l">{E(str(r["사업유형"]))}</td>'
                   f'<td class="l wrap">{E(r["부서"])}</td><td class="c">{d8(r["사업시작일"])} ~ {d8(r["사업완료일"])}</td><td class="c">{E(str(r["수주확도"]))}</td></tr>')
    n_ax = int(c["ax"].sum()); n = len(c)
    cnt = c["k"].value_counts().to_dict()
    return f'''
<div class="view" id="v-proj">
  <div class="titlebar"><h1>프로젝트정보</h1><span class="chip solid">CP관리</span><span class="chip">2026.10.01 · 실주 제외</span>
    <div class="meta2">실제 데이터 · 전체 {n:,}건 · AX사업본부 {n_ax}건</div></div>
  <section class="card-sec" id="p1">
    <div class="sec-head"><h2>구분 규칙</h2><span class="sub">투입계획의 프로젝트코드 = CP 사업코드 + 끝자리 1글자</span></div>
    <div class="rule"><span class="kind k-ex">이행</span> 끝자리 C · W &nbsp; <span class="kind k-pr">제안</span> P &nbsp; <span class="kind k-rd">R&amp;D·내부과제</span> I · N &nbsp; <span class="muted">· CP 사업유형 「비매출」은 끝자리와 관계없이 R&amp;D·내부과제</span>
      <span class="ex">예) CN2600107 + C → CN2600107C (이행) · 아래 목록의 「단계」는 CP 사업단계 기준 참고값이며, 실제 구분은 투입계획에 적힌 끝자리로 정합니다.</span></div>
  </section>
  <section class="card-sec" id="p2">
    <div class="sec-head"><h2>프로젝트 목록</h2><span class="sub">이행 단계 {cnt.get("ex",0)} · 영업 단계 {cnt.get("pr",0)} · 비매출 {cnt.get("rd",0)}</span></div>
    <div class="tabs" role="tablist" id="ptabs">
      <button role="tab" aria-selected="true" data-scope="ax">AX사업본부 ({n_ax})</button><button role="tab" aria-selected="false" data-scope="all">전체 ({n:,})</button>
      <span class="sep"></span>
      <button role="tab" aria-selected="true" data-k="all" class="kf">전체 단계</button><button role="tab" aria-selected="false" data-k="ex" class="kf">이행</button>
      <button role="tab" aria-selected="false" data-k="pr" class="kf">영업</button><button role="tab" aria-selected="false" data-k="rd" class="kf">비매출</button>
      <span class="tools"><input class="tfilter" data-target="ptable-wrap" placeholder="사업명 · 코드 · 부서 필터"></span>
    </div>
    <div class="scroll" data-search id="ptable-wrap"><table id="ptable">
      <thead><tr><th class="l">사업코드</th><th class="l">사업명</th><th class="c">단계</th><th class="l">사업단계</th><th class="l">사업유형</th><th class="l">사업부서</th><th class="c">사업기간</th><th class="c">수주확도</th></tr></thead>
      <tbody>{"".join(trs)}</tbody></table></div>
    <div class="muted" id="pcount" style="margin-top:8px"></div>
  </section>
</div>
'''

CSS = r"""
  td.wrap{white-space:normal;min-width:180px}
  .tabs .sep{width:1px;background:var(--line);margin:6px 8px}
  .tfilter{height:30px;border:1px solid #D1D5DB;padding:0 10px;font:inherit;font-size:12.5px;width:220px;margin-bottom:4px}
  #hr-inc table,#hr-exc table{table-layout:auto}#ptable tbody tr.hide,#hr-inc tbody tr.hide,#hr-exc tbody tr.hide{display:none}
"""
JS = r"""
// HR tabs
document.querySelectorAll('#hrtabs [data-t]').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('#hrtabs [data-t]').forEach(x=>x.setAttribute('aria-selected',x===b));
  ['hr-inc','hr-exc'].forEach(id=>document.getElementById(id).style.display=(id===b.dataset.t)?'':'none');
  document.getElementById('hr-exc-sum').style.display=b.dataset.t==='hr-exc'?'':'none';
}));
// project filters
const pst={scope:'ax',k:'all',q:''};
function pApply(){ let n=0; document.querySelectorAll('#ptable tbody tr').forEach(r=>{
  const ok=(pst.scope==='all'||r.dataset.ax==='1')&&(pst.k==='all'||r.dataset.kind===pst.k)&&(!pst.q||r.textContent.toLowerCase().includes(pst.q));
  r.classList.toggle('hide',!ok); if(ok)n++}); const pc=document.getElementById('pcount'); if(pc)pc.textContent=n.toLocaleString()+'건 표시'; }
document.querySelectorAll('#ptabs [data-scope]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('#ptabs [data-scope]').forEach(x=>x.setAttribute('aria-selected',x===b));pst.scope=b.dataset.scope;pApply()}));
document.querySelectorAll('#ptabs .kf').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('#ptabs .kf').forEach(x=>x.setAttribute('aria-selected',x===b));pst.k=b.dataset.k;pApply()}));
// text filters
document.querySelectorAll('.tfilter').forEach(inp=>inp.addEventListener('input',()=>{
  const q=inp.value.trim().toLowerCase();
  if(inp.dataset.target==='ptable-wrap'){pst.q=q;pApply();return}
  inp.dataset.target.split(',').forEach(id=>document.querySelectorAll('#'+id+' tbody tr').forEach(r=>r.classList.toggle('hide',!!q&&!r.textContent.toLowerCase().includes(q))));
}));
pApply();
"""
