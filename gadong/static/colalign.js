/* 가동ON 표 열 맞춤 — 월(1월~12월) 열이 있는 표는 같은 구역 안에서 월 위치·너비를 똑같이 맞춤
   - 구역 = 가장 가까운 section / details 묶음 / .view
   - 펼침·탭 전환 등으로 새로 보이는 표도 자동으로 다시 맞춤 */
(function(){
  var MRE=/^\s*(\d{1,2})\s*월/, busy=false, timer=null, LAB=320, MON=(window.innerWidth<1260?54:64), TAIL=76, LCAP=150, LFLOOR=84;
  var st=document.createElement('style');st.textContent='@media (max-width:1260px){table.ca-fix td,table.ca-fix th,table.ca-meas td,table.ca-meas th{font-size:11px!important;padding-left:3px!important;padding-right:3px!important}}@media (max-width:1160px){table.ca-fix td,table.ca-fix th,table.ca-meas td,table.ca-meas th{font-size:10.5px!important;padding-left:2px!important;padding-right:2px!important}}table.ca-fix td,table.ca-fix th{overflow:hidden;white-space:nowrap}table.ca-fix td.l,table.ca-fix th.l{white-space:normal!important;text-overflow:clip!important;overflow:visible!important;word-break:keep-all;overflow-wrap:anywhere}table.ca-fix th small{display:block}table.ca-meas td,table.ca-meas th{white-space:nowrap!important}';document.head.appendChild(st);
  function grid(t){ // 머리글 행들을 논리 열로 펼침 → 각 열의 '가장 아래' 머리글 칸
    var rows=t.tHead?t.tHead.rows:[], occ=[], cols=[];
    for(var r=0;r<rows.length;r++){var c=0;occ[r]=occ[r]||[];
      for(var k=0;k<rows[r].cells.length;k++){var th=rows[r].cells[k];while(occ[r][c])c++;
        var cs=th.colSpan||1,rs=th.rowSpan||1;
        for(var i=0;i<rs;i++){occ[r+i]=occ[r+i]||[];for(var j=0;j<cs;j++)occ[r+i][c+j]=1}
        if(cs===1)cols[c]=th; c+=cs}}
    return cols;
  }
  function isM(th){return th&&MRE.test(th.textContent)}
  function scope(t){return t.closest('details.grp')?t.closest('details.grp').parentNode:(t.closest('section,.view,.card,body')||document.body)}
  function run(){
    if(busy)return;busy=true;
    try{
      var tabs=[].slice.call(document.querySelectorAll('table')).filter(function(t){
        if(t.querySelector('colgroup:not([data-auto])')||t.classList.contains('mt')||t.closest('.tp-detail'))return false;
        var g=grid(t);return g.filter(isM).length>=6});
      var groups=new Map();
      tabs.forEach(function(t){if(!t.offsetParent)return;var s=scope(t);if(!groups.has(s))groups.set(s,[]);groups.get(s).push(t)});
      groups.forEach(function(list,sc){
        var info=list.map(function(t){
          var old=t.querySelector(':scope>colgroup[data-auto]');if(old)old.remove();t.classList.remove('ca-fix');
          t.style.tableLayout='auto';t.style.width='max-content';t.style.minWidth='';t.classList.add('ca-meas');   // 글자 그대로의 폭을 잼 (잘림 없이)
          var g=grid(t),first=-1,last=-1;g.forEach(function(th,i){if(isM(th)){if(first<0)first=i;last=i}});
          var w=g.map(function(th){return th?th.getBoundingClientRect().width:60});
          var hid=g.map(function(th){return !!th&&getComputedStyle(th).display==='none'});   // 접힌 월 열 = 폭 0
          t.classList.remove('ca-meas');t.style.width='auto';
          return {t:t,g:g,w:w,first:first,last:last,hid:hid,nest:!!(t.parentElement&&t.parentElement.closest('table'))};
        });
        var lab=0,mon=0,tails=[];
        info.forEach(function(x){var s=0;for(var i=0;i<x.first;i++)s+=x.w[i];lab=Math.max(lab,s);
          for(var i=x.first;i<=x.last;i++)mon=Math.max(mon,x.w[i]);
          for(var i=x.last+1;i<x.w.length;i++){var k=i-x.last-1;tails[k]=Math.max(tails[k]||0,x.w[i])}});
        // 내용과 상관없이 같은 폭: 앞쪽 이름 열 묶음 LAB, 월 MON, 뒤쪽 열 TAIL (넘치는 글자는 … 처리, 마우스 올리면 전체)
        // 앞쪽 이름 열 묶음·뒤쪽 숫자 열은 글자가 다 보이는 폭 이상 (… 잘림 없음) · 월은 MON부터
        mon=MON;
        var sr=sc.getBoundingClientRect?sc.getBoundingClientRect().left:0;
        function inner(el){var cs=getComputedStyle(el);return el.clientWidth-parseFloat(cs.paddingLeft||0)-parseFloat(cs.paddingRight||0)}
        // 폭 나누기 (구역 안 모든 표가 같은 값): 최소 폭(이름 묶음 LAB · 월 MON · 뒤쪽 TAIL)을 먼저 주고
        // 남는 폭은 ① 글자 열(현재·예정 프로젝트·비고 등) +160 → ② 이름 묶음 +80 → ③ 월(최대 140) → ④ 그래도 남으면 글자 열
        var tl0=[];info.forEach(function(x){for(var i=x.last+1;i<x.g.length;i++){var th=x.g[i];if(th&&(th.classList.contains('l')||/프로젝트|비고|후보/.test(th.textContent)))tl0[i-x.last-1]=1}});
        var txt=[];for(var q=0;q<tails.length;q++)if(tl0[q])txt.push(q);
        function nvOf(x){var nv=0;for(var i=x.first;i<=x.last;i++)if(!x.hid[i])nv++;return Math.max(1,nv)}
        function offOf(x){return Math.max(0,Math.round(x.t.getBoundingClientRect().left-sr))}
        var tmin=tails.map(function(w,q){return tl0[q]?120:Math.ceil(w)+2});
        tails=tails.map(function(w,q){w=Math.ceil(w)+2;return tl0[q]?Math.max(TAIL,Math.min(w,200)):Math.max(TAIL,w)});
        var tnat=tails.slice();
        var lwg={};info.forEach(function(x){var a=lwg[x.first]=lwg[x.first]||[];for(var i=0;i<x.first;i++)a[i]=Math.max(a[i]||0,Math.min(LCAP,Math.ceil(x.w[i])+2))});   // 이름 열은 글자 폭(최대 LCAP)까지 — 더 긴 글은 잘리지 않고 줄바꿈
        var LABMIN=LAB;info.forEach(function(x){var a=lwg[x.first],s=0;for(var i=0;i<x.first;i++)s+=a[i];LABMIN=Math.max(LABMIN,s+offOf(x)-24)});
        var LABFLOOR=0;info.forEach(function(x){var a=lwg[x.first],s=0;for(var i=0;i<x.first;i++)s+=Math.min(a[i],LFLOOR);LABFLOOR=Math.max(LABFLOOR,s+offOf(x)-24)});
        var MONMIN=52;info.forEach(function(x){for(var i=x.first;i<=x.last;i++)if(!x.hid[i])MONMIN=Math.max(MONMIN,Math.ceil(x.w[i])+2)});   // 월 칸도 숫자가 잘리지 않는 폭 이하로는 안 줄임
        var tsum=tails.reduce(function(a,b){return a+b},0);
        var top=info.filter(function(x){return !x.nest});if(!top.length)top=info;
        var room=Math.min.apply(null,top.map(function(x){return inner(x.t.parentNode)-Math.max(120,LABMIN-offOf(x)+24)-nvOf(x)*Math.max(MON,MONMIN)-tsum}));
        var LABE=LABMIN,addT=0;mon=Math.max(MON,MONMIN);
        if(room>=0){var r=room;
          if(txt.length){var a1=Math.min(r,160*txt.length);addT+=a1/txt.length;r-=a1}
          var a2=Math.min(r,80);LABE+=a2;r-=a2;
          var mm=Math.min.apply(null,top.map(function(x){return Math.floor((inner(x.t.parentNode)-Math.max(120,LABE-offOf(x)+24)-tsum-addT*txt.length)/nvOf(x))}));
          mon=Math.max(MON,MONMIN,Math.min(110,mm));
          if(txt.length){var r4=Math.min.apply(null,top.map(function(x){return inner(x.t.parentNode)-Math.max(120,LABE-offOf(x)+24)-tsum-addT*txt.length-nvOf(x)*mon}));if(r4>0)addT+=Math.floor(r4/txt.length)}
          if(addT){tails=tails.slice();txt.forEach(function(q){tails[q]+=Math.floor(addT)})}
        }   // 최소 폭으로도 넘치면 아래 반복에서 월 폭만 줄임 (이름·연간 칸은 잘리지 않게, 그래도 넘치면 가로 스크롤)
        // 이름 묶음 안의 열(성명·소속·직무·직급…)도 표마다 같은 비율 → 본부가 달라도 같은 위치
        function apply(){
        info.forEach(function(x){
          var oc=x.t.querySelector(':scope>colgroup[data-auto]');if(oc)oc.remove();
          var off=Math.max(0,Math.round(x.t.getBoundingClientRect().left-sr)),lab=Math.max(120,LABE-off+24);   // 구역 왼쪽 기준으로 월 시작 위치를 고정
          var lw=lwg[x.first]||[],fl=[],sf=0,se=0;for(var i=0;i<x.first;i++){var n=lw[i]||x.w[i];fl[i]=Math.min(n,LFLOOR);sf+=fl[i];se+=n-fl[i]}
          var cg=document.createElement('colgroup');cg.setAttribute('data-auto','1');var tot=0;
          var used=0;
          x.g.forEach(function(th,i){var c=document.createElement('col'),v;
            if(i<x.first){var n=lw[i]||x.w[i];v=(i===x.first-1)?lab-used:Math.floor(lab>=sf?fl[i]+(se?(n-fl[i])*(lab-sf)/se:(lab-sf)/x.first):fl[i]*lab/sf);used+=v}
            else if(i<=x.last)v=x.hid[i]?0:mon;
            else v=(x.tl||tails)[i-x.last-1]||x.w[i];
            if(x.hid[i])return;   // 접힌 열은 col 도 만들지 않음 (숨긴 칸 다음 칸이 당겨져 오므로)
            v=Math.ceil(v);c.style.width=v+'px';tot+=v;cg.appendChild(c)});
          x.t.insertBefore(cg,x.t.firstChild);
          x.t.classList.add('ca-fix');x.t.style.tableLayout='fixed';x.t.style.width=tot+'px';x.t.style.minWidth=tot+'px';
        });
        }
        apply();
        // 그래도 넘치는 표가 있으면(안쪽 상세 패널 등) 구역 전체의 월 폭 → 이름 열 순으로 줄여 다시 맞춤
        for(var k=0;k<10;k++){var ov=0,nvm=12;info.forEach(function(x){var nv=0;for(var i=x.first;i<=x.last;i++)if(!x.hid[i])nv++;nvm=Math.min(nvm,Math.max(1,nv));
            ov=Math.max(ov,x.t.getBoundingClientRect().width-inner(x.t.parentNode))});
          if(ov<=1)break;
          // 1) 넘치는 표 자신의 뒤쪽 열(연간·비고 등)을 먼저 줄임 (안쪽 상세 패널은 바깥 표보다 좁아서) → 2) 그래도 넘치면 구역 전체 월 폭
          var rest=0;info.forEach(function(x){var o=x.t.getBoundingClientRect().width-inner(x.t.parentNode);if(o<=1)return;
            x.tl=(x.tl||tails.slice());for(var q=x.tl.length-1;q>=0&&o>0;q--){var c=Math.min(o,Math.max(0,x.tl[q]-(tmin[q]||44)));x.tl[q]-=c;o-=c}rest=Math.max(rest,o)});
          // 넘치면 ① 월 폭(숫자 안 잘리는 데까지) → ② 이름 열(긴 글은 줄바꿈, 열마다 최소 LFLOOR) 순으로 줄임
          if(rest>1){if(mon>MONMIN)mon=Math.max(MONMIN,mon-Math.ceil(rest/nvm));else if(LABE>LABFLOOR)LABE=Math.max(LABFLOOR,LABE-Math.ceil(rest));else break}
          apply()}
      });
      document.querySelectorAll('table.ca-fix td,table.ca-fix th').forEach(function(c){if(!c.title&&c.scrollWidth>c.clientWidth+1)c.title=c.textContent.trim()});
    }catch(e){}
    setTimeout(function(){busy=false},0);
  }
  function later(){clearTimeout(timer);timer=setTimeout(run,60)}
  window.addEventListener('load',run);window.addEventListener('resize',later);
  document.addEventListener('click',later,true);document.addEventListener('toggle',later,true);
  new MutationObserver(function(ms){if(busy)return;for(var i=0;i<ms.length;i++){var n=ms[i].target;if(n.nodeName==='COLGROUP'||n.nodeName==='COL'||n.nodeName==='TABLE')continue;later();return}})
    .observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['class','open','hidden']});
})();
