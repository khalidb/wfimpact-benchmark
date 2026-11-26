import json,sys,re,html
src,model,scen=sys.argv[1],sys.argv[2],sys.argv[3]
t=open(src).read()
t=html.unescape(t).replace(' ',' ')
t=re.sub(r'\\\s*\n','\n',t)           # RTF-style line continuations
t=t[t.index('{'):t.rindex('}')+1]
a=json.loads(t)
W='/home/claude/state/wfimpact'
json.dump(a,open(f'{W}/llm/answers/web/{model}/{scen}_end_to_end_r1.json','w'),indent=2)
p=f'{W}/runs/{scen}/ground_truth.json'
import os
print('feasible:',a.get('feasible'),'| problems:',a.get('problems','')[:200])
if os.path.exists(p):
    g=json.load(open(p)); tp=fp=fn=0
    for k in ('added','removed','affected'):
        P,T=set(a.get(k,[])),set(g[k]); tp+=len(P&T); fp+=len(P-T); fn+=len(T-P)
        print(f'{k}: pred {len(P)} true {len(T)}  missed {[x.split(":")[-1] for x in sorted(T-P)]}  extra {[x.split(":")[-1] for x in sorted(P-T)]}')
    f1=2*tp/(2*tp+fp+fn) if tp else 0.0
    print('micro F1 %.2f'%f1)
