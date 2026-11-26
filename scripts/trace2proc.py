#!/usr/bin/env python3
"""Summarise a Nextflow execution trace at the process level.

For each process (fully qualified name, sample tag removed) it reports the
number of tasks per status. Status COMPLETED means the task ran in this
execution, CACHED means it was reused from a previous run (with -resume).

Usage:
    python3 trace2proc.py execution_trace.txt -o trace.json
"""
import argparse
import csv
import json
import re
from collections import defaultdict

TAG = re.compile(r'\s*\(.*\)\s*$')


def summarise(path):
    procs = defaultdict(lambda: defaultdict(int))
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            name = TAG.sub('', row['name'])
            procs[name][row['status']] += 1
    return {p: dict(s) for p, s in sorted(procs.items())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('trace', help='execution_trace_*.txt produced by Nextflow')
    ap.add_argument('-o', '--output', help='output JSON file (default: stdout)')
    args = ap.parse_args()

    result = {'source': args.trace, 'processes': summarise(args.trace)}
    data = json.dumps(result, indent=2)
    if args.output:
        open(args.output, 'w').write(data + '\n')
        print(f'{len(result["processes"])} processes -> {args.output}')
    else:
        print(data)


if __name__ == '__main__':
    main()
