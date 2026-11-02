"""화면 정리 — 부연 설명·주석 문구 제거 (관리자/회의용 공통)"""
import re
_SPAN_SUB = re.compile(r'<span class="sub">(?:(?!</span>).)*</span>', re.S)
_DIV = lambda cls: re.compile(r'<div class="%s[^"]*"[^>]*>(?:(?!</div>).)*</div>' % cls, re.S)
def tidy_admin(s):
    s = _SPAN_SUB.sub('', s)
    for c in ('note', 'foot-note', 'demo-switch'):
        s = _DIV(c).sub('', s)
    s = re.sub(r'<span class="chip">(?:(?!</span>).)*</span>', '', s, count=1)
    s = re.sub(r'(<div class="meta2">데이터 기준 <b>[^<]*</b>)[^<]*(</div>)', r'\1\2', s)
    css = '''<style id="tidy-css">
.titlebar{padding:22px 0 22px;gap:10px 16px;align-items:center}
.titlebar h1{font-size:28px;font-weight:800;letter-spacing:-.025em;border-left:0;padding-left:0;line-height:1.15}
.titlebar .chip.solid{font-size:13px;font-weight:700}
.titlebar select{height:34px;font-size:13.5px}
.titlebar .meta2{font-size:12.5px}
.sec-head{margin-bottom:14px}
.sec-head h2{letter-spacing:-.01em}
.conf-all>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px}
.conf-all>summary::-webkit-details-marker{display:none}
.ca-chev{margin-left:auto;width:9px;height:9px;border-right:2px solid var(--steel);border-bottom:2px solid var(--steel);transform:rotate(45deg);transition:transform .15s}
.conf-all:not([open])>summary .ca-chev{transform:rotate(-45deg)}
.conf-all[open]>summary{margin-bottom:14px}
.conf-all .kpi .kg{display:flex;justify-content:center;margin:6px 0 2px}
</style>'''
    return s.replace('</head>', css + '</head>', 1) if '</head>' in s else css + s
def tidy_meeting(s):
    def keep(m):
        t = m.group(0)
        if '<button' in t or '<input' in t or ' id=' in t:
            return '<div class="sub">' + ''.join(re.findall(r'<button.*?</button>|<input[^>]*>', t, re.S)) + '</div>'
        return ''
    for c in ('note', 'rkn', 'sub', 'glg2', 'gleg'):
        s = _DIV(c).sub(keep, s)
    return s
