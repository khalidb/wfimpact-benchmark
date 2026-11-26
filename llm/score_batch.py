#!/usr/bin/env python3
"""Score all API answers (answers/api/<model>/<scenario>_end_to_end_r<k>.json)
against the ground truths in ../runs/<scenario>/ground_truth.json.

Scenarios whose request is infeasible as stated (INFEASIBLE below) have no
added/removed/affected score: they are scored only on whether the model set
"feasible": false. For every other scenario the model should answer
"feasible": true, so a false there counts as a false alarm.

Writes scores.csv (one row per answer) and prints, per model and pipeline,
the mean and standard deviation over scenarios and repetitions.

Usage:
    python3 score_batch.py [--answers answers/api] [--runs ../runs] [-o scores.csv]
"""
import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import match, metrics, parse_answer

HERE = Path(__file__).resolve().parent
INFEASIBLE = {'R10_kallisto', 'A02a_rarefaction_1000', 'A09a_skip_quality'}
NAME = re.compile(r'^(?P<scen>.+)_(?P<task>end_to_end|localisation)_r(?P<rep>\d+)\.json$')


def score_one(answer, truth):
    row, total = {}, [0, 0, 0]
    for cat in ('added', 'removed', 'affected'):
        pairs, extra, missed = match(answer.get(cat, []) or [], truth.get(cat, []))
        m = metrics(len(pairs), len(extra), len(missed))
        row[f'{cat}_f1'] = m['f1']
        total = [total[0] + len(pairs), total[1] + len(extra), total[2] + len(missed)]
    m = metrics(*total)
    row.update(micro_precision=m['precision'], micro_recall=m['recall'], micro_f1=m['f1'])
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--answers', default=str(HERE / 'answers' / 'api'))
    ap.add_argument('--runs', default=str(HERE.parent / 'runs'))
    ap.add_argument('-o', '--output', default=str(HERE / 'scores.csv'))
    args = ap.parse_args()

    rows = []
    for f in sorted(Path(args.answers).glob('*/*.json')):
        m = NAME.match(f.name)
        if not m or m['task'] != 'end_to_end':
            continue
        scen, rep, model = m['scen'], int(m['rep']), f.parent.name
        row = {'model': model, 'pipeline': 'rnaseq' if scen.startswith('R') else 'ampliseq',
               'scenario': scen, 'rep': rep}
        try:
            answer = parse_answer(f)
        except (SystemExit, json.JSONDecodeError) as e:
            row['error'] = f'unparsable answer: {e}'
            rows.append(row)
            continue
        feasible = answer.get('feasible')
        row['predicted_feasible'] = feasible
        if scen in INFEASIBLE:
            row['expected_feasible'] = False
            row['feasibility_correct'] = feasible is False
        else:
            row['expected_feasible'] = True
            row['feasibility_correct'] = feasible is not False
            gt = Path(args.runs) / scen / 'ground_truth.json'
            if gt.is_file():
                row.update(score_one(answer, json.load(open(gt))))
            else:
                row['error'] = f'no ground truth at {gt}'
        rows.append(row)

    if not rows:
        raise SystemExit(f'No answers found under {args.answers}')
    fields = ['model', 'pipeline', 'scenario', 'rep', 'expected_feasible', 'predicted_feasible',
              'feasibility_correct', 'micro_precision', 'micro_recall', 'micro_f1',
              'added_f1', 'removed_f1', 'affected_f1', 'error']
    with open(args.output, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} answers scored -> {args.output}\n')

    groups = defaultdict(list)
    for r in rows:
        groups[(r['model'], r['pipeline'])].append(r)
    fmt = lambda xs: (f'{statistics.mean(xs):.2f} ± {statistics.stdev(xs):.2f}' if len(xs) > 1
                      else f'{xs[0]:.2f}' if xs else '-')
    print(f'{"model":12s} {"pipeline":9s} {"n":>3s}  {"micro F1":14s} {"recall":14s} {"precision":14s} '
          f'{"infeasible flagged":>19s} {"false alarms":>13s}')
    for (model, pipe), rs in sorted(groups.items()):
        f1 = [r['micro_f1'] for r in rs if r.get('micro_f1') is not None]
        rec = [r['micro_recall'] for r in rs if r.get('micro_recall') is not None]
        pre = [r['micro_precision'] for r in rs if r.get('micro_precision') is not None]
        inf = [r for r in rs if r.get('expected_feasible') is False]
        fea = [r for r in rs if r.get('expected_feasible') is True]
        flagged = f"{sum(r['feasibility_correct'] for r in inf)}/{len(inf)}"
        alarms = f"{sum(not r['feasibility_correct'] for r in fea)}/{len(fea)}"
        print(f'{model:12s} {pipe:9s} {len(rs):3d}  {fmt(f1):14s} {fmt(rec):14s} {fmt(pre):14s} '
              f'{flagged:>19s} {alarms:>13s}')
    errors = [r for r in rows if r.get('error')]
    if errors:
        print(f'\n{len(errors)} answers with errors, see the error column of {args.output}')


if __name__ == '__main__':
    main()
