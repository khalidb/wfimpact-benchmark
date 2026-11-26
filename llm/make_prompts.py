#!/usr/bin/env python3
"""Build the LLM prompt pack for the adaptation scenarios.

For a pipeline checked out at a pinned release, this script writes:
  - code_bundle.txt   the workflow source given to the models (one file, reused by all prompts)
  - catalogue.txt     the qualified names of the processes that ran in the baseline
  - prompts/<scenario>/localisation.md and end_to_end.md

Usage:
    python3 make_prompts.py --pipeline ~/nfcore/rnaseq --release 3.28.0 \
        --scenarios ../scenarios/rnaseq --baseline-trace ../baseline_trace.json \
        --requests requests_rnaseq.json -o pack_rnaseq
"""
import argparse
import json
import os
from pathlib import Path

CODE_PARTS = [
    ('main.nf', None),
    ('workflows', '.nf'),
    ('subworkflows', '.nf'),
    ('modules', 'main.nf'),
    ('nextflow.config', None),
    ('conf/base.config', None),
    ('conf/modules.config', None),
    ('conf/modules', '.config'),
    ('conf/ref_databases.config', None),
    ('conf/test.config', None),
]

INTRO = """You are helping a researcher who adapts a community-curated Nextflow pipeline, {pipeline} release {release}, to their own study.

The attached file code_bundle.txt contains the pipeline's source code: workflows, subworkflows, modules and configuration. The pipeline currently runs with its `test` profile, whose parameters are given in conf/test.config inside the bundle. Call this the baseline configuration. In the baseline, the processes listed below are executed. Their names are fully qualified, in the form used in Nextflow execution traces.

Processes executed in the baseline:
{catalogue}

The researcher's request is:

> {request}
"""

LOCALISATION = """## Task

Identify where this request applies in the pipeline. Report:

- `changed_parameters`: the pipeline parameters that must change to implement the request, with their new values;
- `directly_concerned_processes`: the processes concerned directly by the change, that is, processes that are added or removed by it, or whose own command or settings change because of it. Do not include processes that are affected only because their inputs change.

Use the fully qualified naming style of the list above. For processes that do not appear in the list, because they do not run in the baseline, write their qualified name in the same style, as it would appear in an execution trace.

If the request cannot be carried out as stated with this release and the baseline configuration, for instance because the parameters it needs are rejected or a step would fail, set `feasible` to false and explain why in `problems`. Otherwise set `feasible` to true and leave `problems` empty.

Answer with a single JSON object and nothing else, in this format:

```json
{{
  "changed_parameters": [{{"name": "...", "value": "..."}}],
  "directly_concerned_processes": ["..."],
  "feasible": true,
  "problems": "",
  "rationale": "two or three sentences"
}}
```
"""

END_TO_END = """## Task

Predict the impact of this request on the execution of the pipeline, compared with the baseline. Classify processes as follows:

- `added`: processes that run after the change but not in the baseline;
- `removed`: processes that run in the baseline but no longer run after the change;
- `affected`: processes that run in both, but for which at least one task must be executed again because its inputs, command or settings change.

Every other process of the baseline is considered unaffected and must not be listed.

Use the fully qualified naming style of the list above. For processes that do not appear in the list, write their qualified name in the same style, as it would appear in an execution trace.

If the request cannot be carried out as stated with this release and the baseline configuration, for instance because the parameters it needs are rejected or a step would fail, set `feasible` to false and explain why in `problems`. Otherwise set `feasible` to true and leave `problems` empty.

Answer with a single JSON object and nothing else, in this format:

```json
{{
  "changed_parameters": [{{"name": "...", "value": "..."}}],
  "added": ["..."],
  "removed": ["..."],
  "affected": ["..."],
  "feasible": true,
  "problems": "",
  "rationale": "two or three sentences"
}}
```
"""


def bundle(pipeline):
    out = []
    for part, suffix in CODE_PARTS:
        path = pipeline / part
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(p for p in path.rglob('*') if p.is_file() and (suffix is None or p.name.endswith(suffix))
                           and '/tests/' not in str(p))
        else:
            continue
        for f in files:
            out.append(f'===== {f.relative_to(pipeline)} =====\n{f.read_text(encoding="utf-8")}\n')
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pipeline', required=True, type=Path, help='local checkout of the pipeline at the pinned release')
    ap.add_argument('--name', default='nf-core/rnaseq')
    ap.add_argument('--release', required=True)
    ap.add_argument('--baseline-trace', required=True, help='trace2proc.py output for the baseline run')
    ap.add_argument('--requests', required=True, help='JSON mapping scenario name -> natural-language request')
    ap.add_argument('-o', '--output', required=True, type=Path)
    args = ap.parse_args()

    out = args.output
    (out / 'prompts').mkdir(parents=True, exist_ok=True)
    code = bundle(args.pipeline)
    (out / 'code_bundle.txt').write_text(code, encoding='utf-8')

    processes = sorted(json.load(open(args.baseline_trace))['processes'])
    catalogue = '\n'.join(f'- {p}' for p in processes)
    (out / 'catalogue.txt').write_text(catalogue + '\n', encoding='utf-8')

    requests = json.load(open(args.requests))
    for scenario, request in requests.items():
        d = out / 'prompts' / scenario
        d.mkdir(parents=True, exist_ok=True)
        intro = INTRO.format(pipeline=args.name, release=args.release, catalogue=catalogue, request=request)
        (d / 'localisation.md').write_text(intro + '\n' + LOCALISATION.format(), encoding='utf-8')
        (d / 'end_to_end.md').write_text(intro + '\n' + END_TO_END.format(), encoding='utf-8')

    print(f'code bundle: {len(code):,} characters (about {len(code) // 4:,} tokens)')
    print(f'{len(processes)} baseline processes, {len(requests)} scenarios -> {out}')


if __name__ == '__main__':
    main()
