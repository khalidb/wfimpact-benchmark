#!/usr/bin/env bash
# Run one adapted configuration with -resume from the baseline run, so that
# unaffected tasks are reused (CACHED) and affected tasks are re-executed.
# Each scenario gets its own launch directory with a private copy of the
# baseline cache, so scenarios never reuse each other's tasks.
#
# Usage (on an IFB compute node, inside tmux, modules loaded):
#     bash run_scenario.sh scenarios/rnaseq/R01_hisat2.yaml
#     PIPE=ampliseq bash run_scenario.sh scenarios/ampliseq/A01_pooled.yaml
#
# Environment variables:
#     BASE     launch directory of the baseline run (default: ~/rnaseq_test)
#     SESSION  session id of the baseline run (default: read from BASE/.nextflow/history)
# The container path is part of every task hash: keep it identical across runs
export NXF_SINGULARITY_CACHEDIR="${NXF_SINGULARITY_CACHEDIR:-$HOME/singularity_cache}"
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PIPE="${PIPE:-rnaseq}"
source "$HERE/pipelines/$PIPE.env"
SCENARIO="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
NAME="$(basename "$SCENARIO" .yaml)"

if [ -z "${SESSION:-}" ]; then
    # history columns: timestamp, duration, run name, status, revision, session id, command
    SESSION="$(awk -F'\t' '$4 == "OK" && $7 !~ /-preview/ && $7 !~ /-resume/ { s = $6 } END { print s }' "$BASE/.nextflow/history")"
fi
[ -n "$SESSION" ] || { echo "Could not find the baseline session id in $BASE/.nextflow/history"; exit 1; }
echo "Baseline: $BASE  session $SESSION"

RUN="$HERE/runs/$NAME"
if [ -e "$RUN" ]; then
    echo "$RUN already exists, remove it first to rerun this scenario"; exit 1
fi
mkdir -p "$RUN"
cp -r "$BASE/.nextflow" "$RUN/.nextflow"
cp "$SCENARIO" "$RUN/"
cd "$RUN"

nextflow run "$PIPELINE" -r "$REVISION" -profile "$PROFILE" \
    -params-file "$SCENARIO" -work-dir "$BASE/work" -resume "$SESSION" \
    --outdir "$RUN/results" || NF_STATUS=$?
NF_STATUS="${NF_STATUS:-0}"
echo "$NF_STATUS" > nextflow_exit_status.txt
[ "$NF_STATUS" = 0 ] || echo "WARNING: nextflow exited with status $NF_STATUS; tasks that ran (including FAILED ones) still count as executed"

TRACE="$(ls -t results/pipeline_info/execution_trace_*.txt | head -1)"
python3 "$HERE/trace2proc.py" "$TRACE" -o trace.json
python3 "$HERE/taskgraph.py" "$TRACE" -w "$BASE/work" -o provgraph.json

BTRACE="$(ls -t "$BASE"/results/pipeline_info/execution_trace_*.txt | head -1)"
[ -f "${BL}_trace.json" ] || python3 "$HERE/trace2proc.py" "$BTRACE" -o "${BL}_trace.json"

echo
echo "Ground truth for $NAME (from execution):"
python3 "$HERE/compare.py" trace "${BL}_trace.json" trace.json -o ground_truth.json
