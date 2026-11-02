"""가동률·가득률 반원 게이지 SVG (눈금 없음) — 두 게이지를 나란히"""
import math
FONT="font-family=\"Pretendard,'Noto Sans CJK KR','Malgun Gothic',sans-serif\""
try:
    import cfg as _c; _G = _c._C.get("gauge", {})
except Exception:
    _G = {}
LOW = float(_G.get("low", 70)); TARGET = float(_G.get("target", 80))
ZONES = [(50, LOW, '#F3A59D', ''), (LOW, TARGET, '#F6D77A', ''), (TARGET, 100, '#86D6A3', '')]
SC_MIN, SC_MAX = 60.0, 100.0          # 게이지 눈금 범위
UC, GC = '#2A5A9B', '#C77B2B'          # 가동률 파랑 · 가득률 주황

def _th(v):
    v = min(max(v, SC_MIN), SC_MAX)
    return math.radians(180 - (v - SC_MIN) / (SC_MAX - SC_MIN) * 180)
def _p(cx, cy, r, th): return cx + r * math.cos(th), cy - r * math.sin(th)

ZC = [('#F0A39A', '#C0392B'), ('#F6D77A', '#B7791F'), ('#8FD8AE', '#2E8B60')]   # 빨강(<LOW)·노랑(LOW~TARGET)·초록(≥TARGET) 연한색 / 진한색
def _zi(v): return 0 if v < LOW else (1 if v < TARGET else 2)

def _half(cx, cy, R, v, col, label, fv, big, fl='12월 예상'):
    sw = 18; o = []
    edges = [SC_MIN, LOW, TARGET, SC_MAX]
    for k in range(3):
        a, b = edges[k], edges[k + 1]
        xa, ya = _p(cx, cy, R, _th(a)); xb, yb = _p(cx, cy, R, _th(b))
        o.append(f'<path d="M{xa:.1f},{ya:.1f} A{R},{R} 0 0 1 {xb:.1f},{yb:.1f}" fill="none" stroke="{ZC[k][0]}" stroke-width="{sw}"/>')
    for sv in (SC_MIN, LOW, TARGET, SC_MAX):
        if sv in (SC_MIN, SC_MAX): lx, ly = _p(cx, cy, R, _th(sv))[0], cy + 22
        else: lx, ly = _p(cx, cy, R + 22, _th(sv)); ly += 5
        o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" {FONT} font-size="14" font-weight="600" fill="#7B8AA0" text-anchor="middle">{sv:g}</text>')
    th = _th(v); tx, ty = _p(cx, cy, R - 1, th); b1 = _p(cx, cy, 9, th + math.pi / 2); b2 = _p(cx, cy, 9, th - math.pi / 2)
    o.append(f'<polygon points="{tx:.1f},{ty:.1f} {b1[0]:.1f},{b1[1]:.1f} {b2[0]:.1f},{b2[1]:.1f}" fill="{col}"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="9" fill="{col}"/><circle cx="{cx}" cy="{cy}" r="3.4" fill="#fff"/>')
    if v < SC_MIN:   # 눈금(60) 아래: 바늘은 왼쪽 끝에 붙이고 숫자는 빨강, 안에 작게 안내
        col = '#C0392B'
        o.append(f'<text x="{cx}" y="{cy - 30}" {FONT} font-size="14" font-weight="700" fill="#C0392B" text-anchor="middle">{SC_MIN:g}% 미만</text>')
    o.append(f'<text x="{cx}" y="{cy + 46}" {FONT} font-size="{40 if big else 36}" font-weight="800" fill="{col}" text-anchor="middle">{v:.2f}<tspan font-size="{20 if big else 17}" font-weight="700">%</tspan></text>')
    if label:
        o.append(f'<text x="{cx}" y="{cy + (78 if big else 72)}" {FONT} font-size="{25 if big else 18}" font-weight="700" fill="{col}" text-anchor="middle">{label}</text>')
    if fv is not None:
        o.append(f'<text x="{cx}" y="{cy + (98 if label else 76)}" {FONT} font-size="16" fill="#7B8AA0" text-anchor="middle">{fl} <tspan font-weight="700" fill="{col}">{fv:.2f}%</tspan></text>')
    return "".join(o)

def pair(u, g, fu=None, fg=None, uid='p', compact=False, fl='12월 예상'):
    H = 216 if (fu is not None or fg is not None) else 188
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 -14 440 {H}" width="440" height="{H}">']
    o.append(_half(120, 118, 92, g, GC, None, fg, compact, fl))   # 왼쪽 = 가득률 (먼저), 오른쪽 = 가동률
    o.append(_half(340, 118, 92, u, UC, None, fu, compact, fl))
    o.append('</svg>'); return "".join(o)

def dial3(u, g, prev=None, uid='z', zones=None, fu=None, fg=None): return pair(u, g, fu, fg, uid)
def mini(g, u, pg=None, uid='m'): return pair(u, g, None, None, uid, True)

def sized(svg, w):
    import re
    m = re.search(r'viewBox="\S+ \S+ (\d+) (\d+)" width="(\d+)" height="(\d+)"', svg)
    if not m: return svg
    vw, vh = int(m.group(1)), int(m.group(2))
    return svg.replace(f'width="{m.group(3)}" height="{m.group(4)}"', f'width="{w}" height="{round(w * vh / vw)}"', 1)

def ang(v): return -135 + (min(max(v, 50), 100) - 50) / 50 * 270     # 관리자 링 게이지용


def one(v, label, col):
    """단일 반원 게이지 (연간 추정 등)"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 -14 220 190" width="220" height="190">'
            + _half(120, 118, 92, v, col, None, None, True) + '</svg>')
