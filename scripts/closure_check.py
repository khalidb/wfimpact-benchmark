"""Check whether the processes re-executed after an adaptation are exactly the
downstream closure, in the adapted provenance graph, of the entry points
(impacted processes with no impacted predecessor)."""
import json, sys
from collections import defaultdict
def short(p): return p.split(':')[-1]
for run in sys.argv[1:]:
    gt = json.load(open(f'{run}/ground_truth.json'))
    g = json.load(open(f'{run}/provgraph.json'))
    succ, pred = defaultdict(set), defaultdict(set)
    for a, b in g['edges']:
        succ[a].add(b); pred[b].add(a)
    impacted = set(gt['added']) | set(gt['affected'])
    entries = {p for p in impacted if not (pred[p] & impacted)}
    closure, stack = set(entries), list(entries)
    while stack:
        for q in succ[stack.pop()]:
            if q not in closure: closure.add(q); stack.append(q)
    extra, missing = closure - impacted, impacted - closure
    name = run.rstrip('/').split('/')[-1]
    print(f'{name:22s} impacted={len(impacted):3d} entries={len(entries):2d} closure_extra={len(extra)} closure_missing={len(missing)}')
    print('    entries:', sorted(short(p) for p in entries))
    if extra: print('    reachable but cached:', sorted(short(p) for p in extra))
