#!/usr/bin/env python3
"""Score an LLM answer against the ground truth of a scenario.

The answer is the JSON object returned by the model (end_to_end or
localisation task). The ground truth is compare.py's output in trace mode
(ground_truth.json), with lists `added`, `removed` and `affected`.

Process names are matched exactly when possible. Otherwise a predicted name
matches a true name if one is a ':'-separated suffix of the other and the
match is unique, so that "ALIGN_STAR:STAR_ALIGN" can match
"NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN". Unmatched predictions count as
false positives, and unmatched true names as omissions.

Usage:
    python3 score.py answer.json ground_truth.json [-o score.json]
"""
import argparse
import json
import re


def parse_answer(path):
    text = open(path, encoding='utf-8').read()
    m = re.search(r'\{.*\}', text, re.S)   # tolerate prose or code fences around the JSON
    if not m:
        raise SystemExit(f'No JSON object found in {path}')
    return json.loads(m.group(0))


def is_suffix(short, full):
    return full == short or full.endswith(':' + short)


def match(predicted, truth):
    """Return (matched pairs, unmatched predictions, unmatched truths)."""
    truth_left = set(truth)
    pairs, extra = [], []
    predicted = list(dict.fromkeys(predicted))  # a name listed twice counts once
    for p in predicted:
        if p in truth_left:
            pairs.append((p, p)); truth_left.discard(p); continue
        candidates = [t for t in truth_left if is_suffix(p, t) or is_suffix(t, p)]
        if len(candidates) == 1:
            pairs.append((p, candidates[0])); truth_left.discard(candidates[0])
        else:
            extra.append(p)
    return pairs, extra, sorted(truth_left)


def metrics(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision is not None and recall is not None and precision + recall else None)
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': f1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('answer')
    ap.add_argument('truth')
    ap.add_argument('-o', '--output')
    args = ap.parse_args()

    answer = parse_answer(args.answer)
    truth = json.load(open(args.truth, encoding='utf-8'))

    result = {}
    total = [0, 0, 0]
    for category in ('added', 'removed', 'affected'):
        pairs, extra, missed = match(answer.get(category, []), truth.get(category, []))
        m = metrics(len(pairs), len(extra), len(missed))
        m['over_predicted'] = extra
        m['omitted'] = missed
        result[category] = m
        total = [total[0] + len(pairs), total[1] + len(extra), total[2] + len(missed)]

    # Overall impact: any of the three categories, regardless of which one was chosen.
    impacted_truth = set(truth.get('added', [])) | set(truth.get('removed', [])) | set(truth.get('affected', []))
    impacted_pred = list(dict.fromkeys(answer.get('added', []) + answer.get('removed', []) + answer.get('affected', [])))
    pairs, extra, missed = match(impacted_pred, sorted(impacted_truth))
    result['any_impact'] = metrics(len(pairs), len(extra), len(missed))
    result['any_impact'].update(over_predicted=extra, omitted=missed)
    result['micro'] = metrics(*total)

    for k in ('added', 'removed', 'affected', 'any_impact', 'micro'):
        m = result[k]
        fmt = lambda x: '-' if x is None else f'{x:.2f}'
        print(f'{k:10s}  P={fmt(m["precision"])}  R={fmt(m["recall"])}  F1={fmt(m["f1"])}  '
              f'(tp={m["tp"]}, fp={m["fp"]}, fn={m["fn"]})')
    if args.output:
        json.dump(result, open(args.output, 'w'), indent=2)


if __name__ == '__main__':
    main()
