#!/usr/bin/env python3
"""Run every scenario prompt through every model of llm_config.json, with
repetitions, through the providers' APIs (ask_llm.py does each call).

Answers go to answers/api/<model label>/<scenario>_<task>_r<k>.json, with a
.meta.json beside each (model, time, token usage). Existing answers are kept,
so an interrupted batch is resumed by running the same command again.

Usage:
    python3 run_llm_batch.py --config llm_config.json            # everything
    python3 run_llm_batch.py --config llm_config.json --dry-run  # list the calls only
    python3 run_llm_batch.py --config llm_config.json --only claude --scenarios R01_hisat2 --reps 1
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', required=True)
    ap.add_argument('--reps', type=int, help='override the number of repetitions in the config')
    ap.add_argument('--only', nargs='*', help='model labels to run (default: all)')
    ap.add_argument('--scenarios', nargs='*', help='scenario names to run (default: all with prompts)')
    ap.add_argument('--tasks', nargs='*', default=None, help='end_to_end and/or localisation')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    cfg = json.load(open(args.config))
    reps = args.reps or cfg.get('repetitions', 3)
    tasks = args.tasks or cfg.get('tasks', ['end_to_end'])
    models = [m for m in cfg['models'] if not args.only or m['label'] in args.only]

    # Check bundles and keys before spending anything.
    problems = []
    for pipe in cfg['pipelines']:
        if not Path(pipe['bundle']).expanduser().is_file():
            problems.append(f"bundle not found: {pipe['bundle']}")
    for m in models:
        if not os.environ.get(m['key_env']):
            problems.append(f"{m['label']}: environment variable {m['key_env']} is not set")
    if problems and not args.dry_run:
        sys.exit('\n'.join(problems))

    calls = []
    for pipe in cfg['pipelines']:
        prompts = HERE / pipe['pack'] / 'prompts'
        for scen in sorted(p.name for p in prompts.iterdir() if p.is_dir()):
            if args.scenarios and scen not in args.scenarios:
                continue
            for task in tasks:
                for m in models:
                    for k in range(1, reps + 1):
                        out = HERE / 'answers' / 'api' / m['label'] / f'{scen}_{task}_r{k}.json'
                        calls.append((pipe, scen, task, m, k, out))

    todo = [c for c in calls if not c[5].exists()]
    print(f'{len(calls)} calls in total, {len(calls) - len(todo)} already answered, {len(todo)} to do')
    if args.dry_run:
        for pipe, scen, task, m, k, out in todo[:20]:
            print(f"  {m['label']:10s} {scen:28s} {task:12s} r{k}")
        if len(todo) > 20:
            print(f'  ... and {len(todo) - 20} more')
        if problems:
            print('\nTo fix before a real run:\n  ' + '\n  '.join(problems))
        return

    failures = []
    for i, (pipe, scen, task, m, k, out) in enumerate(todo, 1):
        prompt = HERE / pipe['pack'] / 'prompts' / scen / f'{task}.md'
        cmd = [sys.executable, str(HERE / 'ask_llm.py'), '--provider', m['provider'], '--model', m['model'],
               '--bundle', str(Path(pipe['bundle']).expanduser()), '--prompt', str(prompt), '-o', str(out)]
        if m.get('base_url'):
            cmd += ['--base-url', m['base_url']]
        if m.get('temperature') is None:
            cmd.append('--no-temperature')
        else:
            cmd += ['--temperature', str(m['temperature'])]
        env = dict(os.environ)
        if m['provider'] == 'local':
            env['LOCAL_API_KEY'] = os.environ[m['key_env']]
        print(f"[{i}/{len(todo)}] {m['label']} {scen} {task} r{k}", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            msg = (r.stderr or r.stdout).strip().splitlines()[-1:] or ['no output']
            print(f'    FAILED: {msg[0]}', flush=True)
            failures.append(f"{m['label']} {scen} {task} r{k}: {msg[0]}")
            if out.exists():
                out.unlink()
        else:
            print(f'    ok in {time.time() - t0:.0f} s', flush=True)
        time.sleep(cfg.get('pause_seconds', 2))

    print(f'\n{len(todo) - len(failures)} answers saved, {len(failures)} failures')
    for f in failures:
        print('  ' + f)
    print('Run the same command again to retry the failures.')


if __name__ == '__main__':
    main()
