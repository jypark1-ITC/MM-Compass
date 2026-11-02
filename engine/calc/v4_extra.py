import re, datetime as dt

C1, C2 = "#2A5A9B", "#C17A2B"   # 가동률, 가득률 (validated pair)
MON = [f"{i}월" for i in range(1, 13)]

# ---------------- data ----------------
ANN_UTIL = [80.2, 81.0, 82.4, 83.1, 83.8, 84.5, 85.0, 84.2, 85.0, 84.7, 85.6, 86.1]
ANN_GAIN = [67.0, 67.8, 68.9, 69.5, 70.1, 70.8, 71.6, 70.9, 71.5, 71.2, 72.0, 72.4]
ANN_NP   = [74.0, 74.8, 75.9, 76.6, 77.2, 77.9, 78.7, 78.0, 78.4, 78.1, 79.0, 79.4]
CONF = 9  # 1~9월 확정
WEEKS = ["7/6","7/13","7/20","7/27","8/3","8/10","8/17","8/24","8/31","9/7","9/14","9/21","9/28","10/2"]
WEEK_UTIL = [84.1, 84.6, 84.9, 85.2, 83.6, 83.9, 84.0, 84.3, 84.6, 84.0, 84.4, 84.8, 83.0, 84.7]
HQS = [("SI사업본부", [84.0,85.1,86.0,86.4,87.0,87.5,88.2,87.4,88.5,88.4,89.0,89.3]),
       ("SM사업본부", [90.5,90.8,91.0,91.2,91.4,91.6,92.0,91.8,92.0,92.1,92.3,92.4]),
       ("솔루션사업본부", [66.0,67.2,69.5,70.8,71.6,72.9,73.8,72.4,76.0,75.7,77.0,78.2]),
       ("기술연구소", [74.0,73.5,74.5,75.0,74.0,73.2,72.6,73.8,73.0,70.5,72.0,73.5]),
       ("ENT사업본부", [75.0,76.2,77.0,78.1,78.8,79.5,80.0,79.2,82.3,82.5,83.0,83.6])]
def avg(a): return sum(a)/len(a)

# 9월 확정 (본부)
CONF_HQ = [("클로잇","SI사업본부",160.0,141.6),("클로잇","SM사업본부",120.0,110.4),("클로잇","솔루션사업본부",90.0,68.4),
           ("클로잇","기술연구소",40.0,29.2),("아이티센엔텍","ENT사업본부",40.0,32.9)]
assert abs(sum(h[3] for h in CONF_HQ)-382.5) < 1e-6

# ---------------- SVG helpers ----------------
def _smooth(pts):
    if len(pts) < 3: return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts)-1):
        p0 = pts[i-1] if i > 0 else pts[i]; p1 = pts[i]; p2 = pts[i+1]; p3 = pts[i+2] if i+2 < len(pts) else p2
        c1 = (p1[0]+(p2[0]-p0[0])/6, p1[1]+(p2[1]-p0[1])/6); c2 = (p2[0]-(p3[0]-p1[0])/6, p2[1]-(p3[1]-p1[1])/6)
        lo_, hi_ = min(p1[1], p2[1]), max(p1[1], p2[1])
        c1 = (c1[0], min(max(c1[1], lo_), hi_)); c2 = (c2[0], min(max(c2[1], lo_), hi_))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d

_gid = [0]
def line_chart(series, labels, W=1100, H=290, ymin=60, ymax=90, ticks=(60,70,80,90), est_from=None,
               mini=False, unit="%", label_every=1, aria="", cur=None, point_labels=None, pad=None, end_labels=True, left_names=False):
    if point_labels is None: point_labels = not mini
    padL, padR, padT, padB = (40, 18, 24, 22) if mini else (44, 110, 38, 30)
    if pad: padL, padR = pad
    n = len(labels)
    step = (W-padL-padR)/(n-1)
    X = lambda i: padL + i*step
    Y = lambda v: padT + (ymax-v)/(ymax-ymin)*(H-padT-padB)
    fs = 10.5 if mini else 12
    _gid[0] += 1; gid = f"g{_gid[0]}"
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{aria}" class="chart">']
    o.append(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{series[0][1]}" stop-opacity=".16"/><stop offset="1" stop-color="{series[0][1]}" stop-opacity="0"/></linearGradient></defs>')
    if est_from is not None:
        x0 = X(est_from) - step/2; x1 = X(n-1) + min(step/2, 9)
        o.append(f'<rect x="{x0:.1f}" y="{padT-4}" width="{x1-x0:.1f}" height="{H-padT-padB+4}" rx="6" fill="#F5F7FA"/>')
        lx0 = x0; lx1 = x1
        if cur is not None and not mini and cur >= est_from:   # 당월 칸과 겹치지 않게: 당월 뒤쪽(없으면 앞쪽) 예상 구간 가운데에 표시
            if cur < n-1: lx0 = X(cur) + step/2
            elif cur > est_from: lx1 = X(cur) - step/2
            else: lx0 = x0 + step
        if not mini: o.append(f'<text x="{(lx0+lx1)/2:.1f}" y="{padT-10}" font-size="{fs}" fill="#8A94A3" text-anchor="middle" font-weight="600" letter-spacing="1">예상</text>')
    for tv in ticks:
        o.append(f'<line x1="{padL}" x2="{W-padR}" y1="{Y(tv):.1f}" y2="{Y(tv):.1f}" stroke="#E9EDF2" stroke-dasharray="3 4"/>')
        o.append(f'<text x="{padL-8}" y="{Y(tv)+4:.1f}" font-size="{fs}" fill="#9AA3AF" text-anchor="end">{tv}%</text>')
    if cur is not None:
        if mini:
            o.append(f'<rect x="{X(cur)-step/2:.1f}" y="{padT-4}" width="{step:.1f}" height="{H-padT-padB+4}" fill="#0F2942" opacity=".06"/>')
        else:
            bw = min(step, 64)
            o.append(f'<rect x="{X(cur)-bw/2:.1f}" y="{padT-4}" width="{bw:.1f}" height="{H-padT-padB+4}" rx="6" fill="#2A5A9B" opacity=".09"/>')
            o.append(f'<rect x="{X(cur)-25:.1f}" y="{padT-24}" width="50" height="18" rx="9" fill="#0F2942"/>')
            o.append(f'<text x="{X(cur):.1f}" y="{padT-11}" font-size="11" fill="#fff" font-weight="700" text-anchor="middle">당월</text>')
    for i, lb in enumerate(labels):
        if i % label_every == 0 or i == n-1 or i == cur:
            bold = ' font-weight="700" fill="#0F2942"' if i == cur else ' fill="#8A94A3"'
            o.append(f'<text x="{X(i):.1f}" y="{H-8}" font-size="{fs}"{bold} text-anchor="middle">{lb}</text>')
    allpts = []
    for si, (name, color, vals) in enumerate(series):
        pts = [(X(i), Y(v)) if v is not None else None for i, v in enumerate(vals)]; allpts.append(pts)
        runs, cur_run = [], []
        for i, pt in enumerate(pts):
            if pt is None:
                if cur_run: runs.append(cur_run); cur_run = []
            else: cur_run.append((i, pt))
        if cur_run: runs.append(cur_run)
        sw = (2.2 if mini else 2.8) * (0.7 if si > 0 else 1.0)
        for run in runs:
            rp = [pt for _, pt in run]; ri = [i for i, _ in run]
            if si == 0 and len(rp) > 1:
                area = _smooth(rp) + f" L{rp[-1][0]:.1f},{H-padB} L{rp[0][0]:.1f},{H-padB} Z"
                o.append(f'<path d="{area}" fill="url(#{gid})"/>')
            solid = [pt for i, pt in run if est_from is None or i < est_from]
            dash = [pt for i, pt in run if est_from is not None and i >= est_from - 1]
            if len(solid) > 1:
                o.append(f'<path d="{_smooth(solid)}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
            if len(dash) > 1:
                o.append(f'<path d="{_smooth(dash)}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-dasharray="1 6" stroke-linecap="round"/>')
    # ---- 라벨 위치: 두 계열이 가까우면 위·아래로 벌림 ----
    def _sep(pairs, gap):
        """pairs: list of [y, prefer_up(bool)] → 겹치지 않게 조정한 y 리스트"""
        if len(pairs) != 2 or pairs[0][0] is None or pairs[1][0] is None: return [q[0] for q in pairs]
        (y0, _), (y1, _) = pairs
        if abs(y0 - y1) >= gap: return [y0, y1]
        mid = (y0 + y1) / 2
        up0 = y0 <= y1 if abs(y0 - y1) > 0.01 else True
        return [mid - gap/2, mid + gap/2] if up0 else [mid + gap/2, mid - gap/2]
    def _base(si, i, iscur, mini_):
        vals = series[si][2]; pt = allpts[si][i]
        if pt is None: return None
        others = [sv[2][i] for sj, sv in enumerate(series) if sj != si]
        # 위쪽 계열은 점 위, 아래쪽 계열은 점 아래 (같으면 가동률 위·가득률 아래)
        above = (si == 0) if all(ov is None or abs(vals[i]-ov) < 0.6 for ov in others) else all(ov is None or vals[i] >= ov for ov in others)
        y = pt[1]
        if mini_: return y - 9 if above else y + 18
        return (y - 12 if above else y + 21) if iscur else (y - 10 if above else y + 17)
    lab = {}
    for i in range(n):
        iscur = (i == cur)
        if point_labels and iscur:
            ys = _sep([[_base(si, i, iscur, False), True] for si in range(len(series))], 17)
            for si, y in enumerate(ys): lab[(si, i)] = y
    if mini:
        li = cur if cur is not None else n-1
        ys = _sep([[_base(si, li, True, True), True] for si in range(len(series))], 15)
        for si, y in enumerate(ys): lab[("m", si)] = y
    else:
        ends = [allpts[si][-1][1] + 4 if allpts[si][-1] is not None else None for si in range(len(series))]
        ys = _sep([[y, True] for y in ends], 16)
        for si, y in enumerate(ys): lab[("e", si)] = y
        if left_names:
            st_ = [allpts[si][0][1] + 4 if allpts[si][0] is not None else None for si in range(len(series))]
            for si, y in enumerate(_sep([[y, True] for y in st_], 18)): lab[("l", si)] = y
    for si, (name, color, vals) in enumerate(series):
        pts = allpts[si]
        for i, pt in enumerate(pts):
            if pt is None: continue
            x, y = pt
            est = est_from is not None and i >= est_from
            show_pt = (not mini) or i == cur or i == n-1
            if show_pt:
                rr = (3.2 if mini else 4) + (1.3 if i == cur else 0) + (1.5 if (i == cur and not mini) else 0)
                fillc = color if (i == cur and not mini) else ("#fff" if est else color)
                if i == cur and not mini:
                    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr+5:.1f}" fill="{color}" opacity=".15"/>')
                o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr}" fill="{fillc}" stroke="{"#fff" if (i == cur and not mini) else color}" stroke-width="2"/>')
            if (si, i) in lab and lab[(si, i)] is not None:
                iscur = (i == cur)
                fsz = "13" if iscur else "9.5"; fw = "800" if iscur else ("600" if est else "500")
                fc = color
                o.append(f'<text x="{x:.1f}" y="{lab[(si, i)]:.1f}" font-size="{fsz}" font-weight="{fw}" fill="{fc}" text-anchor="middle" paint-order="stroke" stroke="#fff" stroke-width="3">{vals[i]:.2f}%</text>')
        if mini:
            li = cur if cur is not None else n-1
            if pts[li] is None: continue
            pass   # 미니 차트는 수치 라벨 없음 (상단 10월 수치·툴팁으로 확인)
        elif left_names:
            if pts[0] is None: continue
            ly = lab[("e", si)] if False else lab[("l", si)]
            o.append(f'<text x="6" y="{ly:.1f}" font-size="13" fill="{color}" font-weight="700" paint-order="stroke" stroke="#fff" stroke-width="3">{name}</text>')
        elif end_labels:
            if pts[-1] is None: continue
            lx = pts[-1][0]; ly = lab[("e", si)]
            o.append(f'<text x="{lx+12:.1f}" y="{ly:.1f}" font-size="12" fill="{color}" font-weight="700" paint-order="stroke" stroke="#fff" stroke-width="3">{name} {vals[-1]:.2f}%</text>')
    # ---- 마우스 올림: 그 달 세로 띠 전체 → 가동률·가득률을 한 번에 (세로선 + 점 강조) ----
    o.append('<style>.chart .hb .hl{visibility:hidden}.chart .hb:hover .hl{visibility:visible}</style>')
    for i in range(n):
        vs = [(name, color, vals[i]) for name, color, vals in series if vals[i] is not None]
        if not vs: continue
        kind = "" if est_from is None else ("당월" if i == cur else ("실적" if i < est_from else "예상"))
        rows = "".join(f"<br><i style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{c};margin-right:6px'></i>{nm} <b>{v:.2f}{unit}</b>" for nm, c, v in vs)
        if len(vs) == 2: rows += f"<br><span style='opacity:.7'>차이 {abs(vs[0][2]-vs[1][2]):.2f}%p</span>"
        tipv = f"<b>{labels[i]}</b>" + (f" <span style='opacity:.7'>{kind}</span>" if kind else "") + rows
        x0 = X(i) - step/2 if i > 0 else padL - 6; x1 = X(i) + step/2 if i < n-1 else W - padR + 6
        g = [f'<g class="hb" data-tip="{tipv}"><rect x="{x0:.1f}" y="{padT-4}" width="{x1-x0:.1f}" height="{H-padT-padB+4}" fill="transparent"/>',
             f'<line class="hl" x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{padT-4}" y2="{H-padB}" stroke="#0F2942" stroke-opacity=".3" stroke-dasharray="3 3"/>']
        for si, (name, color, vals) in enumerate(series):
            if allpts[si][i] is None: continue
            g.append(f'<circle class="hl" cx="{allpts[si][i][0]:.1f}" cy="{allpts[si][i][1]:.1f}" r="{4.5 if mini else 6}" fill="#fff" stroke="{color}" stroke-width="2.5"/>')
        o.append("".join(g) + "</g>")
    o.append('</svg>')
    return "".join(o)

def legend(items):
    return '<div class="lg">' + "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in items) + \
           '<span><i class="ln"></i>실선 = 실적</span><span><i class="ln dash"></i>점선 = 예상</span></div>'

# ---------------- report: 9월 확정 section ----------------
def confirm_section():
    rows = []
    for corp in ("클로잇", "아이티센엔텍"):
        hs = [h for h in CONF_HQ if h[0] == corp]
        T = sum(h[2] for h in hs); P = sum(h[3] for h in hs)
        rows.append(f'<tr class="sub"><td class="l">{corp} 소계</td><td>{T:.1f} MM</td><td>{P:.1f} MM</td><td>{T-P:.1f} MM</td><td>{P/T*100:.1f}%</td></tr>')
        for h in hs:
            rows.append(f'<tr class="child"><td class="l">{h[1]}</td><td>{h[2]:.1f} MM</td><td>{h[3]:.1f} MM</td><td>{h[2]-h[3]:.1f} MM</td><td>{h[3]/h[2]*100:.1f}%</td></tr>')
    return f'''
  <!-- 0 -->
  <section id="s0" class="card-sec confirm">
    <div class="sec-head"><span class="sec-no lock">월초</span><h2>9월 실적 확정</h2><span class="sub">10.01 확정 · 이후 변경되지 않는 값 · 월 첫 주차에만 표시</span></div>
    <div class="kpis num">
      <div class="kpi fix"><div class="label">가동률</div><div class="value">85.0<small>%</small></div></div>
      <div class="kpi fix"><div class="label">가득률</div><div class="value">71.5<small>%</small></div></div>
      <div class="kpi fix alt"><div class="label">가득률<i>비매출 모수 제외</i></div><div class="value">78.4<small>%</small></div></div>
      <div class="kpi fix"><div class="label">투입 MM</div><div class="value">382.5<small>/ 450.0</small></div></div>
      <div class="kpi fix"><div class="label">대기 MM</div><div class="value">67.5<small>MM</small></div></div>
    </div>
    <details class="conf-more">
      <summary>본부별 9월 확정 실적 보기</summary>
      <div class="scroll"><table>
        <thead><tr><th class="l">법인 / 본부</th><th>가동대상</th><th>투입</th><th>대기</th><th>가동률</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
        <tfoot><tr><td class="l">전체</td><td>450.0 MM</td><td>382.5 MM</td><td>67.5 MM</td><td>85.0%</td></tr></tfoot>
      </table></div>
    </details>
  </section>
'''

# ---------------- report: 인사 변동 section ----------------
HR_CHG = [
 ("입사","p-ok","한○○","클로잇 · SI사업본부 · 공공2팀","10.05","+1.00 MM/월 (10월 0.90)","경력 · 개발 고급"),
 ("입사","p-ok","문○○","클로잇 · SM사업본부 · SM1팀","10.12","+1.00 MM/월 (10월 0.75)","경력 · DBA"),
 ("입사","p-ok","배○○","아이티센엔텍 · ENT사업본부 · ENT개발팀","10.19","+1.00 MM/월 (10월 0.50)","신입"),
 ("퇴사","p-warn","고○○","클로잇 · 솔루션사업본부 · 솔루션개발팀","10.30","−1.00 MM/월 (11월~)","10월은 전월 근무"),
 ("퇴사","p-warn","남○○","클로잇 · 기술연구소 · 연구1팀","10.16","−0.50 MM (10월) · −1.00 (11월~)",""),
 ("휴직","p-mid","유○○","클로잇 · SI사업본부 · 금융1팀","10.12 ~ 2027.01.11","−0.75 MM (10월) · 11~12월 0","육아휴직 · 가동대상 제외"),
 ("복직","p-ok","진○○","클로잇 · SM사업본부 · SM3팀","10.05","+0.90 MM (10월)","휴직 종료"),
 ("전적","p-mid","석○○","클로잇 SI사업본부 → 아이티센엔텍 ENT사업본부","11.01","법인 간 이동 (전체 합계 변동 없음)","법인 이동"),
 ("전배","p-mid","황○○","SI사업본부 공공1팀 → 기술지원팀","10.12","본부 내 이동","부서 이동"),
 ("전배","p-mid","표○○","솔루션사업본부 → SI사업본부 금융1팀","10.19","본부 간 이동","부서 이동"),
]
def hr_section():
    from collections import Counter
    c = Counter(h[0] for h in HR_CHG)
    chips = "".join(f'<span class="hrc"><b>{c.get(k,0)}</b>{k}</span>' for k in ["입사","퇴사","휴직","복직","전적","전배"])
    trs = "".join(f'<tr><td class="c"><span class="pill {p}">{t}</span></td><td class="l">{n}</td><td class="l">{org}</td><td class="c">{d}</td><td class="l">{imp}</td><td class="l muted">{note}</td></tr>' for t,p,n,org,d,imp,note in HR_CHG)
    return f'''
  <!-- HR -->
  <section id="s2" class="card-sec">
    <div class="sec-head"><span class="sec-no">02</span><h2>인사 변동</h2><span class="sub">전주 리포트 이후 등록된 발령 · 인사정보 기준 자동 집계</span></div>
    <div class="hr-sum num">{chips}<span class="hr-net">10월 가동대상 영향 합계 <b>+1.80 MM</b> <em>(입사·복직 +3.05 / 퇴사·휴직 −1.25 · 다음 주차 집계부터 반영)</em></span></div>
    <div class="panel scroll" data-search><table>
      <thead><tr><th class="c">유형</th><th class="l">성명</th><th class="l">소속 (변동)</th><th class="c">적용일</th><th class="l">가동대상MM 영향</th><th class="l">비고</th></tr></thead>
      <tbody>{trs}</tbody>
    </table></div>
  </section>
'''

def transform_report(body):
    # relabel to Oct
    _wr, _wt = weekly_rows()
    body = body.replace("{{HQ_ROWS}}", _wr).replace("<tfoot>{{HQ_TOTAL}}</tfoot>", "<tfoot>" + _wt + "</tfoot>")
    body = body.replace('<thead><tr><th class="l">법인 / 본부</th><th>가동대상</th><th>전주 가동률</th><th>금주 가동률</th><th>증감</th></tr></thead>', WEEKLY_HEAD, 1)
    body = body.replace('<h3>본부별 가동률 증감</h3>', '<h3>본부별 가득률 · 가동률 증감 <span>본부를 누르면 사업부·팀</span></h3>', 1)
    body = body.replace('<div class="row2">', '<div class="row2 wide">', 1)
    body = body.replace("9월 5주차 전주 대비 실적", "10월 2주차 전주 대비 실적").replace("당월(9월) 기준", "당월(10월) 기준")
    body = body.replace("9월 = 당월 · 10~12월 = 투입계획 기준 대기 예정", "10월 = 당월 · 11~12월 = 투입계획 기준 대기 예정")
    body = body.replace("10월 대기", "10월 대기")
    # composition: numbers only
    body = re.sub(r'<td><div class="share"><span class="bar">.*?</span>([0-9.]+%)</div></td>', r'<td>\1</td>', body)
    body = body.replace("막대 = 금주 비중, 세로선 = 전주 비중 · 대기 감소는 개선(초록)으로 표시", "비중 = 가동대상MM 대비 금주 비율 · 대기 감소는 개선(초록)으로 표시")
    body = re.sub(r'<span class="sw" style="background:[^"]+"></span>', '', body)
    # renumber: 02 특이사항->03, 03 대기->04, 04 R&D->05, 05 코멘트->06
    body = body.replace('<span class="sec-no">05</span>', '<span class="sec-no">06</span>')
    body = body.replace('<span class="sec-no">04</span>', '<span class="sec-no">05</span>')
    body = body.replace('<span class="sec-no">03</span>', '<span class="sec-no">04</span>')
    body = body.replace('<span class="sec-no">02</span>', '<span class="sec-no">03</span>')
    body = body.replace('id="s5" class="card-sec"', 'id="s6" class="card-sec"')
    body = body.replace('id="s4" class="card-sec detail"', 'id="s5" class="card-sec detail"')
    body = body.replace('id="s3" class="card-sec sec-3 detail"', 'id="s4" class="card-sec sec-3 detail"')
    body = body.replace('id="s2" class="card-sec"', 'id="s3" class="card-sec"')
    # special issues: comment optional note
    body = body.replace("자동 감지: 전주 대비 가동률 ±3.0%p 이상 · 코멘트는 담당자 입력", "전주 대비 가동률 ±3.0%p 이상 자동 표시 · 코멘트는 있을 때만 표시")
    body = body.replace('<p><em>코멘트</em>ENT운영팀 신규 운영 계약 투입 반영.</p>', '<p class="nocm"><em>코멘트</em>입력된 코멘트 없음 · 연간 추이는 「연간 대시보드」에서 확인</p>')
    # insert confirm + HR sections
    i = body.index("  <!-- 1 -->")
    body = body[:i] + confirm_section() + body[i:]
    j = body.index("  <!-- 2 -->")
    body = body[:j] + hr_section() + body[j:]
    body = body.replace("인쇄 시 탭과 관계없이 전체 법인이 펼쳐진 상태로 출력됩니다.", "월 첫 주차에는 「전월 실적 확정」이 맨 위에 자동으로 표시됩니다.")
    return body

# ---------------- other views ----------------
HQ_T = {"SI사업본부":160.0,"SM사업본부":120.0,"솔루션사업본부":90.0,"기술연구소":40.0,"ENT사업본부":40.0}
HQ_CORP = {"SI사업본부":"아이티센클로잇","SM사업본부":"아이티센클로잇","솔루션사업본부":"아이티센클로잇","기술연구소":"아이티센클로잇","ENT사업본부":"아이티센엔텍"}
GAP = {"SI사업본부":12,"SM사업본부":9,"솔루션사업본부":17,"기술연구소":30,"ENT사업본부":9}
TEAMS = {"SI사업본부":[("공공1팀",45,+2.0),("공공2팀",40,+1.0),("금융1팀",50,-1.5),("기술지원팀",25,-2.6)],
         "SM사업본부":[("SM1팀",45,+1.2),("SM2팀",40,-0.4),("SM3팀",35,-1.1)],
         "솔루션사업본부":[("솔루션개발팀",60,+3.0),("솔루션기획팀",30,-6.0)],
         "기술연구소":[("연구1팀",22,-3.0),("연구2팀",18,+3.7)],
         "ENT사업본부":[("ENT개발팀",16,-2.0),("ENT운영팀",18,+3.0),("ENT기획팀",6,-3.7)]}
HQG = {n: [round(v-GAP[n],1) for v in vals] for n, vals in HQS}
def wavg(names, src):
    T = sum(HQ_T[n] for n in names)
    return [round(sum(HQ_T[n]*src[n][i] for n in names)/T, 1) for i in range(12)]
HQU = dict(HQS)
ALLN = list(HQU)
ANN_UTIL[:] = wavg(ALLN, HQU); ANN_GAIN[:] = wavg(ALLN, HQG)
NP_T = 450-40
ANN_NP[:] = [round(sum(HQ_T[n]*HQG[n][i] for n in ALLN)/NP_T, 1) for i in range(12)]
CORPS = [("아이티센클로잇", [n for n in ALLN if HQ_CORP[n]=="아이티센클로잇"]), ("아이티센엔텍", ["ENT사업본부"])]

def mini_card(title, u, g, extra="", attrs="", sub=None):
    d = u[9]-u[8]
    sub = sub or f'연간 가동 {avg(u):.1f}% · 가득 {avg(g):.1f}%'
    return f'''<div class="mini" {attrs}><div class="mh"><b>{title}</b><span class="cur num"><em>10월</em><strong>{u[9]:.1f}%</strong><i class="{"up" if d>0 else "down"}">{"▲" if d>0 else "▼"}{abs(d):.1f}</i></span></div>
      {line_chart([("가동률", C1, u), ("가득률", C2, g)], MON, W=300, H=176, ymin=30, ymax=100, ticks=(40,70,100), est_from=CONF, mini=True, label_every=3, aria=title+" 월별 가득률·가동률", cur=CONF)}
      <div class="mf num">{sub}</div>{extra}</div>'''

def annual_view(ic):
    util_y, gain_y, np_y = avg(ANN_UTIL), avg(ANN_GAIN), avg(ANN_NP)
    conf_u = avg(ANN_UTIL[:CONF])
    LG = legend([("가동률", C1), ("가득률", C2)])
    main_chart = line_chart([("가동률", C1, ANN_UTIL), ("가득률", C2, ANN_GAIN)], MON, est_from=CONF, cur=CONF, aria="2026년 전사 월별 가득률·가동률 추이")
    corp_cards = ""
    for cname, names in CORPS:
        u = wavg(names, HQU); g = wavg(names, HQG); T = sum(HQ_T[n] for n in names)
        corp_cards += f'''<div class="chart-card corp-card"><div class="ch"><b>{cname}</b><span class="num muted">가동대상 {T:.0f}MM · 연간 가동 {avg(u):.1f}% · 가득 {avg(g):.1f}%</span></div>
          {line_chart([("가동률", C1, u), ("가득률", C2, g)], MON, W=640, H=280, ymin=50, ymax=100, ticks=(50,60,70,80,90,100), est_from=CONF, cur=CONF, aria=cname+" 월별 가득률·가동률")}</div>'''
    minis, panels = {}, ""
    for name, u in HQS:
        g = HQG[name]; key = f"hq{ALLN.index(name)}"
        tag = ""
        minis[HQ_CORP[name]] = minis.get(HQ_CORP[name], "") + mini_card(name, u, g, extra='<div class="more">팀별 현황 보기 ›</div>',
                           attrs=f'data-hq="{key}" tabindex="0" role="button" aria-expanded="false"',
                           sub=f'{HQ_CORP[name]}{tag} · 연간 가동 {avg(u):.1f}% · 가득 {avg(g):.1f}%')
        tminis, trows = "", ""
        for tname, tt, off in TEAMS[name]:
            tu = [round(min(99.5, v+off), 1) for v in u]; tg = [round(max(0, v+off*0.8), 1) for v in g]
            tminis += mini_card(tname, tu, tg)
            trows += f'<tr><td class="l">{tname}</td><td>{tt:.1f} MM</td><td>{tu[8]:.1f}%</td><td>{tg[8]:.1f}%</td><td class="cm">{tu[9]:.1f}%</td><td class="cm">{tg[9]:.1f}%</td><td class="es">{tu[10]:.1f}%</td><td class="es">{tg[10]:.1f}%</td><td class="es">{tu[11]:.1f}%</td><td class="es">{tg[11]:.1f}%</td></tr>'
        panels += f'''<div class="team-panel" id="{key}" hidden>
          <div class="tp-head"><b>{name}</b> 팀별 현황 <span class="muted">· {HQ_CORP[name]} · 팀 {len(TEAMS[name])}개</span><button class="tbtn tp-close" data-close>닫기 ✕</button></div>
          <div class="minis">{tminis}</div>
          <div class="scroll"><table class="tp-tab"><thead><tr><th class="l" rowspan="2">팀</th><th rowspan="2">가동대상<br><small>10월</small></th><th colspan="2">9월 <small>실적</small></th><th colspan="2" class="cm">10월 <small>당월</small></th><th colspan="2" class="es">11월 <small>예상</small></th><th colspan="2" class="es">12월 <small>예상</small></th></tr><tr><th>가동</th><th>가득</th><th class="cm">가동</th><th class="cm">가득</th><th class="es">가동</th><th class="es">가득</th><th class="es">가동</th><th class="es">가득</th></tr></thead><tbody>{trows}</tbody></table></div>
        </div>'''
    def mcells(vals, tag="td"):
        return "".join(f'<{tag} class="{("est" + (" cm" if i==CONF else "")) if i>=CONF else ""}">{v:.1f}</{tag}>' for i, v in enumerate(vals))
    head2 = "".join(f'<th class="{("est" + (" cm" if i==CONF else "")) if i>=CONF else ""}">{m}{"<small>당월</small>" if i==CONF else ""}</th>' for i, m in enumerate(MON))
    rows = annual_table_rows(mcells)
    foot = f'<tr><td class="l">전체</td>{mcells(ANN_UTIL)}<td>{avg(ANN_UTIL):.1f}</td></tr>'
    corp_blocks = ""
    for cname, names in CORPS:
        cu = wavg(names, HQU)
        corp_blocks += f'''<div class="corp-block"><h4 class="corp-h">{cname}<span class="num">본부 {len(names)}개 · 연간 가동 {avg(cu):.1f}% · 10월 {cu[9]:.1f}%</span></h4>
          <div class="minis hq-minis">{minis[cname]}</div></div>'''
    return f'''
<div class="view" id="v-annual">
  <div class="titlebar"><h1>연간 대시보드</h1><span class="chip solid">2026년</span><span class="chip">1~9월 실적 · 10~12월 예상</span>
    <div class="meta2">매주 업로드 데이터가 누적되어 자동 갱신 · 최종 <b>10.02 17:40</b></div></div>
  <section class="card-sec" id="a1">
    <div class="sec-head"><span class="sec-no">01</span><h2>전사 총괄</h2><span class="sub">아이티센클로잇 + 아이티센엔텍 · 연간 = 1~12월 평균(실적+예상)</span></div>
    <div class="kpis num k4">
      <div class="kpi"><div class="label">연간 가동률</div><div class="value">{util_y:.1f}<small>%</small></div><div class="ytd">1~9월 실적 평균 {conf_u:.1f}%</div></div>
      <div class="kpi"><div class="label">연간 가득률</div><div class="value">{gain_y:.1f}<small>%</small></div><div class="ytd">1~9월 실적 평균 {avg(ANN_GAIN[:CONF]):.1f}%</div></div>
      <div class="kpi alt"><div class="label">가득률<i>비매출 모수 제외</i></div><div class="value">{np_y:.1f}<small>%</small></div><div class="ytd">연간 기준 · 임원 등 비매출 모수 제외</div></div>
      <div class="kpi"><div class="label">실적 확정</div><div class="value">9<small>/ 12개월</small></div><div class="ytd">다음 확정: 10월 실적 (11월 1주차)</div></div>
    </div>
    <div class="chart-card"><div class="ch"><b>월별 가득률 · 가동률</b>{LG}</div>{main_chart}</div>
  </section>
  <section class="card-sec" id="a2">
    <div class="sec-head"><span class="sec-no">02</span><h2>법인별 연간 흐름</h2><span class="sub">법인별로 업로드한 데이터 기준</span>{LG}</div>
    <div class="corp-grid">{corp_cards}</div>
  </section>
  <section class="card-sec" id="a3">
    <div class="sec-head"><span class="sec-no">03</span><h2>본부별 연간 추이</h2><span class="sub">동일 눈금(30~100%) · ▲▼ = 9월 대비 10월 가동률 · 본부를 누르면 팀별 현황</span>{LG}</div>
    {corp_blocks}
    <div class="tp-hint muted">본부 카드를 누르면 그 본부 바로 아래에 팀별 현황이 펼쳐집니다.</div>
    {panels}
  </section>
  <section class="card-sec" id="a4">
    <div class="sec-head"><span class="sec-no">04</span><h2>2026년 본부별 가동률</h2><span class="sub">단위 % · 회색 음영 = 예상 · 파란 테두리 = 당월(10월) · 본부를 누르면 사업부·팀, 조직을 누르면 월별 실적(MM)</span></div>
    <div class="scroll"><table class="mtab">
      <thead><tr><th class="l" rowspan="2">법인 / 본부</th><th colspan="{CONF}" class="grp-c">실적</th><th colspan="{12-CONF}" class="grp-e">예상</th><th rowspan="2">연간</th></tr>
      <tr>{head2}</tr></thead>
      <tbody>{rows}</tbody><tfoot>{foot}</tfoot></table></div>
  </section>
</div>
'''

CSS_ANN = r"""
  .corp-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .corp-card{margin-top:0}
  .sec-head .lg{margin-left:12px}
  .hq-minis > .mini{cursor:pointer;transition:border-color .15s}
  .hq-minis > .mini:hover{border-color:var(--steel)}
  .hq-minis > .mini.sel{border:2px solid var(--navy);background:#FAFBFD;box-shadow:0 4px 0 -2px var(--navy)}
  .mini .more{font-size:11.5px;color:var(--steel);font-weight:600;margin-top:4px}
  .mini.sel .more{color:var(--navy)}
  .tp-hint{margin-top:10px;font-size:12px}
  .team-panel{grid-column:1/-1;position:relative;margin-top:6px;border:2px solid var(--navy);padding:14px;background:#FAFBFD}
  .team-panel::before{content:"";position:absolute;top:-11px;left:calc(var(--cx,40px) - 10px);border:10px solid transparent;border-top:0;border-bottom-color:var(--navy)}
  .team-panel::after{content:"";position:absolute;top:-8px;left:calc(var(--cx,40px) - 8px);border:8px solid transparent;border-top:0;border-bottom-color:#FAFBFD}
  .team-panel .minis{display:grid}
  .tp-head{display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:14px;color:var(--navy)}
  .tp-head .tp-close{margin-left:auto;height:30px}
  .team-panel .minis{grid-template-columns:repeat(4,1fr);margin-bottom:12px}
  .team-panel .mini{background:#fff}
  th small{font-weight:500;color:var(--steel)}
  @media (max-width:1100px){ .corp-grid{grid-template-columns:1fr} .team-panel .minis{grid-template-columns:repeat(2,1fr)} }
  @media (max-width:860px){ .team-panel .minis{grid-template-columns:1fr} }
"""
JS_ANN = r"""
// 본부 → 팀별 현황 (선택한 본부 바로 아래 줄에 펼침)
const hqCards=[...document.querySelectorAll('.hq-minis > .mini')];
let openCard=null;
function placePanel(card){
  const p=document.getElementById(card.dataset.hq);
  const grid=card.parentElement; const sib=[...grid.querySelectorAll(':scope > .mini')];
  const rowCards=sib.filter(c=>Math.abs(c.offsetTop-card.offsetTop)<4);
  rowCards[rowCards.length-1].after(p);
  const g=grid.getBoundingClientRect(), c=card.getBoundingClientRect();
  p.style.setProperty('--cx',(c.left-g.left+c.width/2)+'px');
}
function openHq(card){
  const was=card===openCard;
  hqCards.forEach(c=>{c.classList.remove('sel');c.setAttribute('aria-expanded','false')});
  document.querySelectorAll('.team-panel').forEach(p=>p.hidden=true);
  openCard=null; const hint=document.querySelector('.tp-hint');
  if(was){hint.style.display='';return}
  card.classList.add('sel');card.setAttribute('aria-expanded','true');openCard=card;hint.style.display='none';
  const p=document.getElementById(card.dataset.hq); p.hidden=false; placePanel(card);
  window.scrollTo({top:card.getBoundingClientRect().top+scrollY-80,behavior:'smooth'});
}
hqCards.forEach(c=>{c.addEventListener('click',()=>openHq(c));c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openHq(c)}})});
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();if(openCard)openHq(openCard)}));
window.addEventListener('resize',()=>{if(openCard)placePanel(openCard)});
"""

def upload_view(ic):
    return f'''
<div class="view" id="v-upload">
  <div class="titlebar"><h1>투입계획 업로드</h1><span class="crumb">담당 부서의 투입계획 파일을 올리면 자동으로 취합됩니다</span></div>
  <span class="mock-note">화면 구성 예시 · 실제 기능은 사이트 구축 단계에서 구현</span>
  <div class="up-grid">
    <div>
      <div class="steps">
        <div><b>1. 양식 확인</b>인력롤링 양식 그대로 사용</div>
        <div><b>2. 파일 업로드</b>여러 팀이 섞여 있어도 OK</div>
        <div><b>3. 자동 인식</b>시트·헤더·팀 자동 매칭</div>
        <div><b>4. 확인 후 반영</b>변경 내역 확인 → 저장</div>
      </div>
      <section class="card-sec" id="u1">
        <div class="drop">{ic('upload', 34)}<b>파일을 여기로 끌어오거나 선택하세요</b>.xlsx · 투입현황 시트 포함 (가동대상MM은 인사정보로 자동 계산)
          <div class="row"><button class="tbtn">파일 선택</button><button class="tbtn">양식 다운로드</button></div></div>
      </section>
      <section class="card-sec" id="u2">
        <div class="sec-head"><h2>최근 업로드</h2><span class="sub">내 업로드 기준</span></div>
        <table><thead><tr><th class="l">일시</th><th class="l">파일명</th><th class="l">인식된 팀</th><th>인원</th><th class="c">결과</th></tr></thead>
        <tbody><tr><td class="l">10.02 16:12</td><td class="l">SI사업본부_투입계획_1002.xlsx</td><td class="l">공공1팀 외 3개</td><td>162</td><td class="c"><span class="pill p-ok">반영 완료</span></td></tr>
        <tr><td class="l">09.25 15:40</td><td class="l">SI사업본부_투입계획_0925.xlsx</td><td class="l">공공1팀 외 3개</td><td>160</td><td class="c"><span class="pill p-ok">반영 완료</span></td></tr></tbody></table>
      </section>
    </div>
    <aside class="card-sec side" id="u3">
      <div class="sec-head"><h2>이번 주 제출 현황</h2><span class="sub">마감 10.02(금) 18:00</span></div>
      <div class="role"><span class="chip solid">관리자</span> 전체 본부 표시 · 담당자 로그인 시 본인 담당 부서만 표시</div>
      <div class="big num">18 <small>/ 20개 팀</small></div>
      <div class="prog"><i style="width:90%"></i></div>
      <ul class="sub-list">
        <li><span>SI사업본부</span><b class="num">4/4</b><span class="pill p-ok">완료</span></li>
        <li><span>SM사업본부</span><b class="num">3/3</b><span class="pill p-ok">완료</span></li>
        <li><span>솔루션사업본부</span><b class="num">1/2</b><span class="pill p-warn">미제출 1</span></li>
        <li><span>기술연구소</span><b class="num">2/2</b><span class="pill p-ok">완료</span></li>
        <li><span>ENT사업본부 <em>엔텍</em></span><b class="num">2/3</b><span class="pill p-warn">미제출 1</span></li>
      </ul>
      <button class="tbtn wide">미제출 담당자에게 알림</button>
    </aside>
  </div>
</div>
'''

# business-day calc for HR sample
HOL = {dt.date(2026,10,5), dt.date(2026,10,9), dt.date(2026,12,25)}
def bdays(y, m, start=None, end=None):
    d = dt.date(y, m, 1); n = 0; tot = 0
    while d.month == m:
        if d.weekday() < 5 and d not in HOL:
            tot += 1
            if (start is None or d >= start) and (end is None or d <= end): n += 1
        d += dt.timedelta(days=1)
    return n, tot

PEOPLE = [
 ("한○○","클로잇","SI사업본부","공공2팀","개발 · 고급","2026-10-05",None,None,"입사"),
 ("유○○","클로잇","SI사업본부","금융1팀","PM","2019-03-04",None,("2026-10-12","2027-01-11"),"휴직"),
 ("진○○","클로잇","SM사업본부","SM3팀","운영 · 중급","2021-07-01",None,None,"복직 (10.05)"),
 ("고○○","클로잇","솔루션사업본부","솔루션개발팀","개발 · 중급","2022-01-03","2026-10-30",None,"퇴사 예정"),
 ("남○○","클로잇","기술연구소","연구1팀","아키텍트","2018-05-14","2026-10-16",None,"퇴사"),
 ("문○○","클로잇","SM사업본부","SM1팀","DBA","2026-10-12",None,None,"입사"),
 ("석○○","클로잇","SI사업본부","공공1팀","PL","2020-02-03",None,None,"11.01 엔텍 전적 예정"),
 ("배○○","아이티센엔텍","ENT사업본부","ENT개발팀","개발 · 초급","2026-10-19",None,None,"입사"),
 ("김○○","클로잇","SI사업본부","기술지원팀","QA","2017-09-01",None,None,""),
 ("이○○","아이티센엔텍","ENT사업본부","ENT운영팀","운영 · 중급","2023-04-03",None,None,""),
]
def mm_for(join, leave, leave_rng, y, m):
    s = dt.date.fromisoformat(join); e = dt.date.fromisoformat(leave) if leave else None
    n, tot = bdays(y, m, s, e)
    if leave_rng:
        a, b = (dt.date.fromisoformat(x) for x in leave_rng)
        off, _ = bdays(y, m, max(a, s), min(b, e) if e else b)
        n -= off
    return max(n, 0) / tot

def hr_view(ic):
    _, t10 = bdays(2026,10); _, t11 = bdays(2026,11); _, t12 = bdays(2026,12)
    trs = ""
    for nm, corp, hq, team, job, j, l, lr, note in PEOPLE:
        mm = [mm_for(j, l, lr, 2026, m) for m in (10, 11, 12)]
        cells = "".join(f'<td class="{"zero" if v==0 else ("part" if v<1 else "")}">{v:.2f}</td>' for v in mm)
        lv = f'{lr[0][5:].replace("-",".")} ~ {lr[1][2:].replace("-",".")}' if lr else "—"
        trs += f'<tr><td class="l">{nm}</td><td class="l">{corp}</td><td class="l">{hq}</td><td class="l">{team}</td><td class="l">{job}</td><td class="c">{j.replace("-",".")}</td><td class="c">{l.replace("-",".") if l else "—"}</td><td class="c">{lv}</td>{cells}<td class="l muted">{note}</td></tr>'
    return f'''
<div class="view" id="v-hr">
  <div class="titlebar"><h1>인사정보</h1><span class="crumb">재직·발령 정보로 사람별·월별 가동대상MM을 자동 계산합니다</span></div>
  <span class="mock-note">화면 구성 예시</span>
  <div class="src-grid" id="h1">
    <section class="card-sec src on"><div class="sec-head"><h2>① 인사정보 파일 업로드</h2><span class="pill p-ok">사용 중</span></div>
      <p>인사 시스템에서 내려받은 재직자 목록(입사일·퇴사일·휴직기간·소속)을 올리면 기존 정보와 비교해 <b>입사·퇴사·휴직·전적·전배</b>를 자동으로 찾아 반영합니다.</p>
      <div class="row"><button class="tbtn">파일 선택</button><button class="tbtn">양식 다운로드</button><span class="muted">최종 반영 10.02 09:10 · 관리자</span></div></section>
    <section class="card-sec src"><div class="sec-head"><h2>② 사내 인사시스템 연동</h2><span class="pill p-mid">검토 중</span></div>
      <p>IT팀에서 DB 조회 또는 API 제공이 가능하면 매일 자동으로 가져옵니다. 연동이 되면 ① 업로드 없이 같은 화면이 그대로 갱신됩니다.</p>
      <div class="row"><span class="muted">확인 필요: 연동 방식(DB/API) · 조회 권한 · 갱신 주기</span></div></section>
  </div>
  <section class="card-sec" id="h2">
    <div class="sec-head"><h2>가동대상MM 계산 규칙</h2></div>
    <div class="rule num">가동대상MM = 통합인사정보 「주소속」 월별 값 (재직 영업일 ÷ 전체 영업일 · 휴직 기간 제외)<span class="ex">대상: 가동여부 <b>Y</b> · 직원구분 <b>정규직 · 촉탁직 · 임원</b> (계약직 제외) · 임원은 비매출 모수로 별도 집계</span>
      <span class="ex">영업일: 10월 {t10}일 · 11월 {t11}일 · 12월 {t12}일 &nbsp;|&nbsp; 예) 10.05 입사 → 10월 {bdays(2026,10,dt.date(2026,10,5))[0]}/{t10} = {bdays(2026,10,dt.date(2026,10,5))[0]/t10:.2f} MM</span></div>
  </section>
  <section class="card-sec" id="h3">
    <div class="sec-head"><h2>인원별 가동대상MM</h2><span class="sub">샘플 10명 · 1 미만은 일할 계산된 달</span></div>
    <div class="scroll" data-search><table>
      <thead><tr><th class="l">성명</th><th class="l">법인</th><th class="l">본부</th><th class="l">팀</th><th class="l">직무</th><th class="c">입사일</th><th class="c">퇴사일</th><th class="c">휴직</th><th>10월</th><th>11월</th><th>12월</th><th class="l">비고</th></tr></thead>
      <tbody>{trs}</tbody></table></div>
  </section>
</div>
'''

PROJS = [
 ("26-0412C","금융 차세대 시스템 구축","이행","클로잇","SI사업본부","2026.03 ~ 2027.06",42,40.5),
 ("26-0388W","공공 클라우드 전환 2단계","이행","클로잇","SI사업본부","2026.05 ~ 2026.12",31,30.2),
 ("26-0101C","통신 SM 운영","이행","클로잇","SM사업본부","2026.01 ~ 2026.12",58,57.0),
 ("26-0455P","제조 MES 구축 제안","제안","클로잇","SI사업본부","2026.09 ~ 2026.10",9,7.5),
 ("26-0461P","공공 클라우드 3단계 제안","제안","클로잇","SI사업본부","2026.10 ~ 2026.11",6,4.8),
 ("26-0210I","AI 문서분석 엔진","R&D","클로잇","기술연구소","2026.02 ~ 2026.12",11,8.0),
 ("26-0215N","표준 개발프레임워크 정비","내부과제","클로잇","SI사업본부","2026.06 ~ 2026.12",5,4.0),
 ("26-E031C","보안관제 운영","이행","아이티센엔텍","ENT사업본부","2026.01 ~ 2026.12",14,13.6),
 ("26-E040I","보안관제 솔루션 개발","R&D","아이티센엔텍","ENT사업본부","2026.04 ~ 2026.12",4,3.0),
]
def proj_view(ic):
    kc = {"이행": "k-ex", "제안": "k-pr", "R&D": "k-rd", "내부과제": "k-in"}
    trs = "".join(f'<tr data-kind="{"rd" if k in ("R&D","내부과제") else ("ex" if k=="이행" else "pr")}"><td class="l mono">{c}</td><td class="l">{n}</td><td class="c"><span class="kind {kc[k]}">{k.replace("&","&amp;")}</span></td><td class="l">{corp}</td><td class="l">{hq}</td><td class="c">{per}</td><td>{p}</td><td>{mm:.1f}</td></tr>' for c,n,k,corp,hq,per,p,mm in PROJS)
    return f'''
<div class="view" id="v-proj">
  <div class="titlebar"><h1>프로젝트정보</h1><span class="crumb">프로젝트 코드 기준 구분 자동 분류 · 투입현황과 연결</span></div>
  <span class="mock-note">화면 구성 예시</span>
  <section class="card-sec" id="p1">
    <div class="sec-head"><h2>구분 자동 분류 규칙</h2><span class="sub">코드 마지막 글자</span></div>
    <div class="rule"><span class="kind k-ex">이행</span> C · W &nbsp; <span class="kind k-pr">제안</span> P &nbsp; <span class="kind k-rd">R&amp;D</span> I &nbsp; <span class="kind k-in">내부과제</span> N &nbsp; <span class="muted">· CP 사업유형 「비매출」은 끝자리와 관계없이 R&amp;D·내부과제</span></div>
  </section>
  <section class="card-sec" id="p2">
    <div class="sec-head"><h2>프로젝트 목록</h2><span class="sub">10월 투입 기준</span></div>
    <div class="tabs" role="tablist" id="ptabs">
      <button role="tab" aria-selected="true" data-k="all">전체</button><button role="tab" aria-selected="false" data-k="ex">이행</button>
      <button role="tab" aria-selected="false" data-k="pr">제안</button><button role="tab" aria-selected="false" data-k="rd">R&amp;D·내부과제</button>
      <span class="tools"><button>프로젝트 파일 업로드</button></span>
    </div>
    <div class="scroll" data-search><table id="ptable">
      <thead><tr><th class="l">코드</th><th class="l">프로젝트명</th><th class="c">구분</th><th class="l">법인</th><th class="l">주관 본부</th><th class="c">기간</th><th>투입 인원</th><th>10월 MM</th></tr></thead>
      <tbody>{trs}</tbody></table></div>
  </section>
</div>
'''

def master_view():
    return '''
<div class="view" id="v-master">
  <div class="titlebar"><h1>기준정보</h1><span class="crumb">취합·계산에 쓰이는 기준값 (관리자 전용)</span></div>
  <span class="mock-note">화면 구성 예시</span>
  <section class="card-sec" id="m1">
    <table><thead><tr><th class="l">항목</th><th class="l">내용</th><th class="c">최종 수정</th></tr></thead>
    <tbody>
      <tr><td class="l">조직 체계</td><td class="l">법인 &gt; 본부 &gt; 사업부 &gt; 팀 (클로잇 / 아이티센엔텍 ENT사업본부)</td><td class="c">09.01</td></tr>
      <tr><td class="l">비매출 모수</td><td class="l">직원구분 「임원」 — 가동대상에는 포함, 비매출 모수 제외 가득률의 분모에서 제외</td><td class="c">09.01</td></tr>
      <tr><td class="l">영업일 캘린더</td><td class="l">한국 공휴일 + 회사 지정 휴일 · 월별 표준근로시간</td><td class="c">01.02</td></tr>
      <tr><td class="l">특이사항 기준</td><td class="l">전주 대비 가동률 ±3.0%p 이상 자동 표시</td><td class="c">09.29</td></tr>
      <tr><td class="l">확정 실적</td><td class="l">월 확정 시 고정 (1~__ACTM__월 확정)</td><td class="c">10.01</td></tr>
      <tr><td class="l">사용자 · 권한</td><td class="l">관리자 / 담당자(담당 부서 지정)</td><td class="c">09.15</td></tr>
    </tbody></table>
  </section>
</div>
'''.replace('__ACTM__', str(__import__('cfg').ACTM))

CSS = r"""
  .s3{background:var(--warn-bg);color:var(--warn)}
  .confirm{border-left:4px solid var(--navy)}
  .sec-no.lock{background:var(--navy)!important;color:#fff!important}
  .kpi.fix{border-top-width:1px;border-top-color:var(--line)}
  .kpi.fix .value{margin-bottom:2px}
  .kpi.fix.alt{border-top:3px solid var(--steel)}
  details.conf-more{margin-top:12px;border:1px solid var(--line)}
  details.conf-more>summary{font-size:12.5px;color:var(--steel);font-weight:600;padding:8px 14px}
  .hr-sum{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  .hrc{border:1px solid var(--line);padding:4px 12px;font-size:12.5px;color:var(--muted);background:#fff}
  .hrc b{color:var(--navy);font-size:16px;margin-right:5px}
  .hr-net{margin-left:auto;font-size:12.5px;color:var(--muted)}
  .hr-net b{color:var(--good)}
  .hr-net em{font-style:normal;font-size:11.5px}
  td.muted,.muted{color:var(--muted);font-size:12px}
  .issue p.nocm{color:var(--muted)}
  .chart-card{border:1px solid var(--line);padding:12px 14px;margin-top:14px}
  .chart-card .ch{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px}
  .chart-card .ch b{font-size:13px;color:var(--navy)}
  .lg{display:flex;gap:14px;font-size:11.5px;color:var(--muted);flex-wrap:wrap}
  .lg i{display:inline-block;width:12px;height:3px;margin-right:5px;vertical-align:3px}
  .lg i.ln{background:#6B7280}.lg i.ln.dash{background:repeating-linear-gradient(90deg,#6B7280 0 4px,transparent 4px 7px)}
  .k4{grid-template-columns:repeat(4,1fr)!important}
  .minis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
  @media (max-width:1300px){.minis{grid-template-columns:repeat(3,1fr)}}
  @media (max-width:860px){.minis{grid-template-columns:1fr}}
  .mini{border:1px solid var(--line);padding:10px 12px}
  .mh{display:flex;justify-content:space-between;align-items:baseline;font-size:12.5px}
  .mh b{color:var(--navy)}.mh em{font-style:normal;font-size:11.5px;margin-left:4px}
  .mf{font-size:11px;color:var(--muted)}
  table.mtab td,table.mtab th{padding:6px 8px}
  th.fut,td.fut{background:#F6F8FB}
  table.mtab td.est{color:var(--steel)}
  table.mtab .e1{border-left:2px dashed var(--steel)}
  table.mtab th.est{color:var(--steel);font-weight:600}
  table.mtab th.grp-c{background:var(--navy);color:#fff;text-align:center;letter-spacing:.05em}
  table.mtab th.grp-e{background:#fff;color:var(--steel);text-align:center;border-bottom:2px solid var(--steel)}
  table.mtab tfoot td.est{color:#C9D6E3}
  table.mtab tfoot .e1{border-left-color:#7F9BB8}
  .corp-block+.corp-block{margin-top:18px}
  .corp-h{font-size:14px;color:var(--navy);margin-bottom:10px;padding-left:10px;border-left:4px solid var(--navy);display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .corp-h span{font-size:12px;color:var(--muted);font-weight:500}
  .tip{position:fixed;pointer-events:none;background:#0F2942;color:#fff;font-size:12.5px;line-height:1.7;padding:8px 11px;z-index:60;display:none;border-radius:4px;white-space:nowrap;box-shadow:0 4px 14px rgba(15,41,66,.25)}
  .up-grid{display:grid;grid-template-columns:1fr 300px;gap:16px;align-items:start}
  .side .role{font-size:11.5px;color:var(--muted);margin-bottom:10px;line-height:1.6}
  .side .big{font-size:28px;font-weight:700;color:var(--navy)}
  .side .big small{font-size:13px;color:var(--muted);font-weight:500}
  .sub-list{list-style:none;margin:12px 0;display:flex;flex-direction:column}
  .sub-list li{display:grid;grid-template-columns:1fr 40px 70px;align-items:center;gap:6px;font-size:12.5px;padding:7px 0;border-bottom:1px solid var(--line)}
  .sub-list li em{font-style:normal;font-size:10.5px;color:var(--steel)}
  .sub-list .pill{text-align:center}
  .tbtn.wide{width:100%;justify-content:center}
  .src-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .src-grid .card-sec{margin-bottom:16px}
  .src p{font-size:13px;margin-bottom:12px}
  .src .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .src:not(.on){background:#FAFBFC;border-style:dashed}
  .rule{font-size:13px;background:var(--bg-sub);padding:12px 14px;line-height:1.8}
  .rule .ex{display:block;font-size:12px;color:var(--muted)}
  td.part{color:var(--steel);font-weight:700}
  .mono{font-family:Consolas,monospace;font-size:12px}
  .k-ex{background:var(--navy);color:#fff}.k-pr{background:var(--steel);color:#fff}
  .k-rd{background:#7F9BB8!important;color:#fff!important}
  @media (max-width:1550px){ .gnb a{padding:0 10px;font-size:14px} .search{width:180px} .user div{display:none} .topbar{gap:12px} }
  @media (max-width:1300px){ .tbtn span.t{display:none} .brand small{display:none} .search{width:160px} }
  @media (max-width:1100px){ .up-grid{grid-template-columns:1fr} .gnb a{padding:0 7px;font-size:13px} }
  @media (max-width:860px){ .src-grid{grid-template-columns:1fr} .k4{grid-template-columns:repeat(2,1fr)!important} .hr-net{margin-left:0} }
  @media print{ .conf-more{display:block} .tip{display:none!important} .kpis>*{min-width:0} .kpi .value{font-size:14pt!important} .kpi .label i{display:block;width:max-content;margin:2px 0 0} .confirm{border-left:none} }
"""

JS_BASE = r"""
// tooltip
const tip=document.createElement('div');tip.className='tip';document.body.appendChild(tip);
document.addEventListener('mouseover',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');if(!t){tip.style.display='none';return}tip.innerHTML=t.dataset.tip;tip.style.display='block'});
document.addEventListener('mousemove',e=>{const w=tip.offsetWidth,h=tip.offsetHeight;tip.style.left=(e.clientX+14+w>innerWidth?e.clientX-w-14:e.clientX+14)+'px';tip.style.top=(e.clientY+14+h>innerHeight?e.clientY-h-14:e.clientY+14)+'px'});
// other rails: scroll to anchors
document.querySelectorAll('.rail .grp:not([data-for=report]) a').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();
  a.parentElement.querySelectorAll('a').forEach(x=>x.classList.toggle('on',x===a));
  const el=document.querySelector(a.getAttribute('href')); if(el) window.scrollTo({top:el.getBoundingClientRect().top+scrollY-76,behavior:'smooth'})}));
// print: open confirm detail

"""

CSS = CSS + CSS_ANN
JS = JS_BASE + JS_ANN

exec(open(__import__('cfg').c("org_mod.py"),encoding="utf-8").read())
exec(open(__import__('cfg').c("real_mod.py"),encoding="utf-8").read())
CSS = CSS + ORG_CSS + WEEKLY_CSS
JS = JS + ORG_JS.replace("__ORG__", ORG_JSON)

# ADMIN_V1
