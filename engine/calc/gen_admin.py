import random, html
random.seed(7)

SUR = list("김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진나지엄채원천방공현함변염여추도석선설마길위연표명기반왕금옥육인맹제모탁국어은편용")
def nm(): return random.choice(SUR) + "○○"
def f1(t): return f"{t/10:.1f}"
def split(total_t, choices):
    out = []
    while total_t > 0:
        v = min(total_t, random.choice(choices))
        if total_t - v in (1, 2): v = total_t  # avoid tiny leftovers
        out.append(v); total_t -= v
    return out

# ---------- 본부 (가동대상, 전주 투입, 금주 투입) in tenths ----------
HQ = [
  # corp, name, target, prev_in, cur_in, teams, jobs
  ("cloit", "SI사업본부", 1600, 1376, 1414, ["공공1팀","공공2팀","금융1팀","기술지원팀"]),
  ("cloit", "SM사업본부", 1200, 1098, 1105, ["SM1팀","SM2팀","SM3팀"]),
  ("cloit", "솔루션사업본부", 900, 646, 681, ["솔루션개발팀","솔루션기획팀"]),
  ("cloit", "기술연구소", 400, 302, 282, ["연구1팀","연구2팀"]),
  ("entec", "ENT사업본부", 400, 314, 330, ["ENT개발팀","ENT운영팀","ENT기획팀"]),
]
CORP = {"cloit": "클로잇", "entec": "아이티센엔텍"}
JOBS = ["개발 · 초급","개발 · 중급","개발 · 고급","PM","PL","아키텍트","QA","DBA","운영 · 중급","기획","디자인"]
PLANS_OK = ["유통 SM 이관","공공 구축 2단계","통신 SM 증원","금융 차세대 이행","제품 고도화"]
PLANS_MID = ["금융 차세대 제안","공공 클라우드 제안","제조 MES 제안","SI 제안 지원"]
MONTH_START = {"10.06","10.13","10.01","10.20","10.27"}

# ---------- 대기인력 ----------
idle_groups = []
for corp, hq, tgt, pin, cin, teams in HQ:
    idle_t = tgt - cin
    ppl = []
    for v in split(idle_t, [10,10,10,10,10,5,8,6,4,3]):
        rs = random.random()
        if rs < 0.38:
            start = random.choice(["10.12","10.19","10.26","11.02"])
            m10, m11 = 0, 0
            st = ("확정","p-ok"); plan = f"{random.choice(PLANS_OK)} ({start})"
        elif rs < 0.78:
            m10, m11 = random.choice([5,10,10]), random.choice([0,0,5,10])
            st = ("협의 중","p-mid"); plan = random.choice(PLANS_MID)
        else:
            m10, m11 = 10, random.choice([10,10,5])
            st = ("배치 필요","p-warn"); plan = "미정"
        ms = [v, m10, m11]
        streak = 0
        for m in ms:
            if m: streak += 1
            else: break
        ppl.append(dict(n=nm(), team=random.choice(teams), job=random.choice(JOBS), ms=ms, tot=sum(ms), st=st, plan=plan, streak=streak))
    ppl.sort(key=lambda p: -p["tot"])
    idle_groups.append((corp, hq, idle_t, ppl))

# ---------- R&D + 내부과제 ----------
PROJ = [
  ("cloit","R&D","AI 문서분석 엔진","기술연구소","연구2팀",80),
  ("cloit","R&D","복권 플랫폼 선행개발","솔루션사업본부","솔루션개발팀",105),
  ("cloit","R&D","데이터 파이프라인 고도화","기술연구소","연구1팀",62),
  ("cloit","내부과제","표준 개발프레임워크 정비","SI사업본부","기술지원팀",40),
  ("cloit","내부과제","사내 업무시스템 개선","솔루션사업본부","솔루션기획팀",35),
  ("cloit","내부과제","운영 자동화 툴 구축","SM사업본부","SM1팀",20),
  ("entec","R&D","보안관제 솔루션 개발","ENT사업본부","ENT개발팀",30),
  ("entec","내부과제","품질관리 체계 구축","ENT사업본부","ENT기획팀",10),
]
CONV = ["금융 차세대 (이행)","공공 클라우드 (제안)","제품 고도화 (이행)","유통 SM 이관 (이행)","미정"]
proj = []
for corp, kind, pname, hq, team, mm in PROJ:
    ppl = []
    for v in split(mm, [10,10,10,5,8,6]):
        c = random.choice(CONV)
        st = ("검토 필요","p-warn") if c == "미정" else random.choice([("확정","p-ok"),("협의 중","p-mid"),("협의 중","p-mid")])
        ppl.append(dict(n=nm(), team=team, mm=v, conv=c, st=st, mon=("—" if c=="미정" else random.choice(["10월","11월","12월"]))))
    ppl.sort(key=lambda p: -p["mm"])
    proj.append((corp, kind, pname, hq, team, mm, ppl))

assert sum(p[5] for p in proj) == 382
assert sum(g[2] for g in idle_groups) == 688

# ---------- HTML pieces ----------
def pct(a, b): return a / b * 100
def dcls(d): return "up" if d > 0.04 else ("down" if d < -0.04 else "flat")
def sgn(d): return ("+" if d > 0.04 else ("−" if d < -0.04 else "±")) + f"{abs(d):.1f}"

# 본부 table
rows = []
def hq_row(name, tgt, pin, cin, cls=""):
    p0, p1 = round(pct(pin, tgt), 1), round(pct(cin, tgt), 1)
    d = p1 - p0
    return f'<tr class="{cls}"><td class="l">{name}</td><td>{f1(tgt)} MM</td><td>{p0:.1f}%</td><td>{p1:.1f}%</td><td class="{dcls(d)}">{sgn(d)}%p</td></tr>'
for corp in ("cloit","entec"):
    hs = [h for h in HQ if h[0]==corp]
    T = sum(h[2] for h in hs); P = sum(h[3] for h in hs); C = sum(h[4] for h in hs)
    rows.append(hq_row(f"{CORP[corp]} 소계", T, P, C, "sub"))
    for h in hs:
        nm_ = h[1] + ""
        rows.append(hq_row(nm_, h[2], h[3], h[4], "child"))
TT = sum(h[2] for h in HQ); TP = sum(h[3] for h in HQ); TC = sum(h[4] for h in HQ)
assert (TT, TP, TC) == (4500, 3736, 3812), (TT, TP, TC)
hq_table = "\n".join(rows)
hq_total = hq_row("전체", TT, TP, TC).replace("<tr", "<tr").replace('class=""','')

# idle section
def idle_html():
    out = []
    for corp, hq, idle_t, ppl in idle_groups:
        need = sum(1 for p in ppl if p["st"][0]=="배치 필요")
        trs = []
        for p in ppl:
            badge = (f'<span class="streak s{p["streak"]}">{"연말까지" if p["streak"]==3 else str(p["streak"])+"개월 연속"}</span>' if p["streak"]>=3 else "")
            cells = "".join(f'<td class="{"zero" if m==0 else ""}{" fut" if i else " cm"}">{f1(m)}</td>' for i,m in enumerate(p["ms"]))
            trs.append(f'<tr><td class="l">{p["n"]} {badge}</td><td class="l">{p["team"]}</td><td class="l">{p["job"]}</td>{cells}<td class="strong">{f1(p["tot"])}</td><td class="l">{p["plan"]}</td><td class="c"><span class="pill {p["st"][1]}">{p["st"][0]}</span></td></tr>')
        out.append(f'''
<details class="grp" data-corp="{corp}">
  <summary>
    <span class="g-name"><span class="corp-chip {corp}">{CORP[corp]}</span>{hq}</span>
    <span class="g-m"><em>인원</em>{len(ppl)}명</span>
    <span class="g-m"><em>10월 대기</em>{f1(idle_t)} MM</span>
    <span class="g-m"><em>배치 필요</em><b class="{"down" if need else ""}">{need}명</b></span>
    <span class="chev" aria-hidden="true"></span>
  </summary>
  <div class="scroll"><table>
    <thead><tr><th class="l">성명</th><th class="l">팀</th><th class="l">직무</th><th class="cm">10월<br><small>당월</small></th><th class="fut">11월</th><th class="fut">12월</th><th>10~12월 합</th><th class="l">투입 예정</th><th class="c">상태</th></tr></thead>
    <tbody>{"".join(trs)}</tbody>
  </table></div>
</details>''')
    return "\n".join(out)

def proj_html():
    out = []
    for corp, kind, pname, hq, team, mm, ppl in proj:
        trs = "".join(f'<tr><td class="l">{p["n"]}</td><td class="l">{p["team"]}</td><td>{f1(p["mm"])}</td><td class="l"><span class="arrow">→</span>{p["conv"]}</td><td class="c">{p["mon"]}</td><td class="c"><span class="pill {p["st"][1]}">{p["st"][0]}</span></td></tr>' for p in ppl)
        kc = "k-rd" if kind=="R&D" else "k-in"
        out.append(f'''
<details class="grp" data-corp="{corp}">
  <summary>
    <span class="g-name"><span class="kind {kc}">{html.escape(kind)}</span>{pname}</span>
    <span class="g-org">{hq} · {team}</span>
    <span class="g-m"><em>인원</em>{len(ppl)}명</span>
    <span class="g-m"><em>10월</em>{f1(mm)} MM</span>
    <span class="chev" aria-hidden="true"></span>
  </summary>
  <div class="scroll"><table>
    <thead><tr><th class="l">성명</th><th class="l">팀</th><th>10월 MM</th><th class="l">전환 후보 프로젝트</th><th class="c">전환 예정</th><th class="c">상태</th></tr></thead>
    <tbody>{trs}</tbody>
  </table></div>
</details>''')
    return "\n".join(out)

idle_cnt = sum(len(g[3]) for g in idle_groups)
idle_cnt_c = sum(len(g[3]) for g in idle_groups if g[0]=="cloit")
idle_need = sum(1 for g in idle_groups for p in g[3] if p["st"][0]=="배치 필요")
idle_streak = sum(1 for g in idle_groups for p in g[3] if p["streak"]==3)
rd_c = sum(p[5] for p in proj if p[0]=="cloit"); rd_e = sum(p[5] for p in proj if p[0]=="entec")
rd_n = sum(len(p[6]) for p in proj)

tpl = open(__import__('cfg').w("tpl4.html"), encoding="utf-8").read()
out = (tpl.replace("{{HQ_ROWS}}", hq_table).replace("{{HQ_TOTAL}}", hq_total)
          .replace("{{IDLE}}", idle_html()).replace("{{PROJ}}", proj_html())
          .replace("{{IDLE_CNT}}", str(idle_cnt)).replace("{{IDLE_CNT_C}}", str(idle_cnt_c))
          .replace("{{IDLE_CNT_E}}", str(idle_cnt-idle_cnt_c)).replace("{{IDLE_NEED}}", str(idle_need))
          .replace("{{IDLE_STREAK}}", str(idle_streak))
          .replace("{{RD_C}}", f1(rd_c)).replace("{{RD_E}}", f1(rd_e)).replace("{{RD_N}}", str(rd_n))
          .replace("{{PROJ_N}}", str(len(proj))))
assert "{{" not in out
open(__import__('cfg').w("admin.html"), "w", encoding="utf-8").write(out)
print("idle", idle_cnt, idle_need, idle_streak, "rd people", rd_n)
