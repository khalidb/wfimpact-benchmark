# Predicting the impact of workflow adaptations: benchmark and results

This repository accompanies the paper *Predicting the Impact of Workflow Adaptations with LLMs* (RCIS 2027). It contains a benchmark of 26 adaptation requests on two nf-core pipelines, the execution-based ground truth of each request, the prompts given to the LLMs, their answers, and the scripts used to produce and score everything.

## Benchmark

| Pipeline | Release | Profile | Processes in the baseline run |
|---|---|---|---|
| [nf-core/rnaseq](https://nf-co.re/rnaseq/3.28.0) | 3.28.0 | `test` | 65 |
| [nf-core/ampliseq](https://nf-co.re/ampliseq/3.1.0) | 3.1.0 | `test` | 79 |

`benchmark/benchmark.md` (or `.csv`) lists every request with its kind, its wording, the configuration that implements it, its feasibility, the size of its impact and the F1 of each predictor. Each request is implemented as a Nextflow parameters file applied on top of the `test` profile (`benchmark/scenarios/`). The wording given to the LLMs is in `benchmark/requests_*.json`.

Five kinds of adaptation occur in both pipelines: tool substitution, step removal, step addition, change of reference data and change of an analysis setting. Three requests are infeasible as stated: `R10_kallisto` and `A09a_skip_quality` are rejected by the pipeline, and `A02a_rarefaction_1000` fails at run time. `R10b_kallisto_valid` and `A09b_skip_quality_valid` are the repaired variants, and `A02b_rarefaction_600` stands for the failing request.

## Ground truth

Each pipeline is run once with its test profile, as the baseline. Each adaptation is then run with `-resume` from the baseline, so that Nextflow reuses every task whose inputs and command are unchanged. Comparing the two runs gives, per process:

- **added**: runs only in the adapted pipeline;
- **removed**: ran only in the baseline;
- **affected**: in both, with at least one task executed again;
- **unaffected**: in both, with every task reused.

`results/runs/<scenario>/` holds, for each feasible request, `ground_truth.json` (the four sets), `trace.json` (a summary of the execution trace) and `provgraph.json` (the graph of the run, rebuilt from the files that tasks use and generate). The baseline traces and process graphs are in `results/baselines/`.

For the oracle to be sound, all runs must use the same container directory, input files must be identified by name and size (`process.cache = 'lenient'`), and the work directories created by each adaptation must be deleted afterwards, keeping those of the baseline. `scripts/slurm/` contains the batch scripts we used on a SLURM cluster, which do this.

## Predictors

- **LLM predictor.** The prompt (`llm/prompts/<pipeline>/<scenario>.md`) contains the request and the list of processes of the baseline run (`catalogue.txt`). The source code of the release is attached as a single file, the *code bundle*. The ampliseq bundle is included. The rnaseq bundle is produced in the same way by `llm/make_prompts.py`. Answers are JSON objects listing the changed parameters, the processes added, removed and affected, a judgement of feasibility and a rationale.
- **Models.** Claude Opus 5.5 and GPT-6.2, both at medium reasoning effort, through their web interfaces, in new conversations without memory and with web search disabled (`llm/answers/notes.txt`). Answers are in `llm/answers/claude/` and `llm/answers/gpt/`.
- **Structural predictor.** Nextflow's `-preview` on the adapted configuration (`results/previews/`, produced by `scripts/run_previews.sh`), with propagation from the consumers of removed processes along the baseline process graph.
- **Hybrid predictor.** The LLM's prediction, completed by propagation from its affected processes along the baseline process graph.

Scores are in `results/scores/`. `llm/save_answer.py` scores one answer against the ground truth.

## Layout

```
benchmark/          requests, implementations and the summary table
scripts/            ground truth: run_scenario.sh, setup_baseline.sh, run_previews.sh,
                    taskgraph.py (graph from work directories), compare.py, dag2proc.py
scripts/pipelines/  pipeline settings (release, profile, paths)
scripts/slurm/      batch scripts used on the cluster (paths to adapt)
llm/                prompt generation, scoring, prompts and answers
results/            ground truth, baselines, previews and scores
```

## Reproducing

Requirements: Nextflow, Singularity (or Docker) and Python 3. Set the paths in `scripts/pipelines/*.env`, run the baseline with the `test` profile, then `scripts/setup_baseline.sh` and `scripts/run_scenario.sh benchmark/scenarios/<pipeline>/<scenario>.yaml` for each request. The cluster scripts contain paths specific to our environment, which must be adapted.

## Licence

Code under the MIT licence, data and results under CC BY 4.0. The code bundle reproduces the source of nf-core/ampliseq, which is distributed under the MIT licence by its authors.
