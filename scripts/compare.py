#!/usr/bin/env python3
"""Compare an original and an adapted workflow run, structurally and from execution.

Three comparisons are available. Each can be used on its own.

  graph   Structural difference between the process graphs (dag2proc.py output)
          of the original and adapted configurations: processes added and removed.
          With --changed, also computes the processes reachable downstream of the
          given changed processes in the adapted graph (the structural baseline
          for the propagation task).

  trace   Ground truth from execution. The adapted run must have been launched
          with -resume from the original run, so that unaffected tasks are CACHED
          and affected tasks are re-executed (COMPLETED). Reports processes added,
          removed, affected (at least one task re-executed) and unaffected.

  check   Graph against trace for a single run: processes present in the graph
          that never executed (structural over-approximation).

Usage:
    python3 compare.py graph original_graph.json adapted_graph.json [--changed P ...]
    python3 compare.py trace original_trace.json adapted_trace.json
    python3 compare.py check graph.json trace.json
Add -o result.json to save the result.
"""
import argparse
import json
from collections import defaultdict


def load(path):
    return json.load(open(path, encoding='utf-8'))


def reachable(edges, sources):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
    seen, frontier = set(), list(sources)
    while frontier:
        node = frontier.pop()
        for nxt in adj[node]:
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return seen - set(sources)


def cmp_graph(orig, adapt, changed):
    o, a = set(orig['processes']), set(adapt['processes'])
    unknown = [p for p in changed if p not in a]
    result = {
        'added': sorted(a - o),
        'removed': sorted(o - a),
    }
    if changed:
        result['changed'] = sorted(changed)
        result['unknown_changed'] = unknown
        result['downstream_of_changed'] = sorted(reachable(adapt['edges'], changed))
    return result


def cmp_trace(orig, adapt):
    o, a = orig['processes'], adapt['processes']
    affected, unaffected = [], []
    for p in sorted(set(o) & set(a)):
        executed = sum(a[p].get(s, 0) for s in ('COMPLETED', 'FAILED', 'ABORTED'))
        (affected if executed > 0 else unaffected).append(p)
    return {
        'added': sorted(set(a) - set(o)),
        'removed': sorted(set(o) - set(a)),
        'affected': affected,
        'unaffected': unaffected,
    }


def check(graph, trace):
    g, t = set(graph['processes']), set(trace['processes'])
    return {
        'in_graph_not_executed': sorted(g - t),
        'executed_not_in_graph': sorted(t - g),
        'graph_processes': len(g),
        'executed_processes': len(t),
    }


def show(result):
    for key, value in result.items():
        if isinstance(value, list):
            print(f'{key} ({len(value)})')
            for item in value:
                print(f'    {item}')
        else:
            print(f'{key}: {value}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['graph', 'trace', 'check'])
    ap.add_argument('first')
    ap.add_argument('second')
    ap.add_argument('--changed', nargs='*', default=[], help='qualified names of changed processes (graph mode)')
    ap.add_argument('-o', '--output', help='save the result as JSON')
    args = ap.parse_args()

    first, second = load(args.first), load(args.second)
    if args.mode == 'graph':
        result = cmp_graph(first, second, args.changed)
    elif args.mode == 'trace':
        result = cmp_trace(first, second)
    else:
        result = check(first, second)

    show(result)
    if args.output:
        json.dump(result, open(args.output, 'w'), indent=2)


if __name__ == '__main__':
    main()
