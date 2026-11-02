import re, sys
p=sys.argv[1]; full=open(p,encoding='utf-8').read()
a=full.index('<div class="view" id="v-hr">'); b=full.index('<div class="view" id="v-master">')
protected=full[a:b]; s=full[:a]+'\x01PROTECTED\x01'+full[b:]
# 1) 법인명 통일
s=s.replace('아이티센클로잇','\x00').replace('클로잇','아이티센클로잇').replace('\x00','아이티센클로잇')
# 2) 소수점 둘째 자리 (텍스트 노드 + data-tip 속성만, script/style 제외)
num=re.compile(r'(?<![\d.])(\d+\.\d)(?![\d.])')
def fix(t): return num.sub(lambda m:m.group(1)+'0', t)
out=[]; pos=0
for m in re.finditer(r'<(script|style)\b.*?</\1>', s, re.S):
    out.append(('h', s[pos:m.start()])); out.append(('r', m.group(0))); pos=m.end()
out.append(('h', s[pos:]))
res=[]
for kind, chunk in out:
    if kind=='r': res.append(chunk); continue
    parts=re.split(r'(<[^>]*>)', chunk)
    for i,pt in enumerate(parts):
        if pt.startswith('<'):
            pt=re.sub(r'data-tip="([^"]*)"', lambda m:'data-tip="'+fix(m.group(1))+'"', pt)
            parts[i]=pt
        else:
            parts[i]=fix(pt)
    res.append(''.join(parts))
s=''.join(res).replace('\x01PROTECTED\x01', protected)
import tidy as _tidy; s=_tidy.tidy_admin(s)
open(p,'w',encoding='utf-8').write(s)
print('done', len(re.findall(r'\d+\.\d\d', s)))
