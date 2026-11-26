#!/usr/bin/env python3
"""Rebuild the data dependency graph of a Nextflow run from its work directory.

Nextflow stages a task's inputs as symbolic links pointing into the work
directories of the tasks that produced them. Following these links gives the
exact task-level dependency graph of the run (retrospective provenance),
which this script also aggregates at the process level.

Run it on the machine where the run took place, from the launch directory:

    python3 taskgraph.py results/pipeline_info/execution_trace_*.txt -w work -o provgraph.json

For a run launched with -resume, CACHED tasks point to the work directories of
the earlier run, which is expected.
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict

TAG = re.compile(r'\s*\(.*\)\s*$')
HASH_DIR = re.compile(r'^([0-9a-f]{2})/([0-9a-f]{30})')


def load_trace(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def task_dir(workdir, short_hash):
    matches = glob.glob(os.path.join(workdir, short_hash + '*'))
    return matches[0] if len(matches) == 1 else None


def producers(directory, workdir):
    """Yield the 'xx/full_hash' keys of task directories that this task's inputs link to."""
    # The work directory may be reached through different spellings
    # (e.g. /shared/home/... versus a symlinked home), so try both.
    bases = {os.path.abspath(workdir), os.path.realpath(workdir)}
    for root, dirs, files in os.walk(directory, followlinks=False):
        for name in dirs + files:
            path = os.path.join(root, name)
            if not os.path.islink(path):
                continue
            # Follow one level only: the link points to the direct producer.
            target = os.readlink(path)
            if not os.path.isabs(target):
                target = os.path.normpath(os.path.join(root, target))
            for base in bases:
                if target.startswith(base + os.sep):
                    m = HASH_DIR.match(os.path.relpath(target, base))
                    if m:
                        yield f'{m.group(1)}/{m.group(2)}'
                    break


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('trace', help='execution_trace_*.txt of the run')
    ap.add_argument('-w', '--workdir', default='work', help='Nextflow work directory (default: work)')
    ap.add_argument('-o', '--output', help='output JSON file (default: stdout)')
    args = ap.parse_args()

    rows = load_trace(args.trace)
    by_dir, info, missing = {}, {}, []
    for row in rows:
        d = task_dir(args.workdir, row['hash'])
        if d is None:
            missing.append(row['name'])
            continue
        m = HASH_DIR.search(os.path.relpath(d, args.workdir))
        key = f'{m.group(1)}/{m.group(2)}'
        by_dir[key] = row['name']
        info[row['name']] = {'process': TAG.sub('', row['name']), 'status': row['status'], 'dir': d}

    task_edges = set()
    for name, meta in info.items():
        for key in producers(meta['dir'], args.workdir):
            src = by_dir.get(key)
            if src and src != name:
                task_edges.add((src, name))

    proc_edges = {(info[a]['process'], info[b]['process']) for a, b in task_edges
                  if info[a]['process'] != info[b]['process']}
    result = {
        'source': args.trace,
        'processes': sorted({m['process'] for m in info.values()}),
        'edges': sorted(map(list, proc_edges)),
        'task_edges': sorted(map(list, task_edges)),
        'tasks_without_workdir': missing,
    }
    data = json.dumps(result, indent=2)
    if args.output:
        open(args.output, 'w').write(data + '\n')
        print(f'{len(result["processes"])} processes, {len(result["edges"])} process edges, '
              f'{len(result["task_edges"])} task edges, {len(missing)} tasks without work dir -> {args.output}')
    else:
        print(data)


if __name__ == '__main__':
    main()
