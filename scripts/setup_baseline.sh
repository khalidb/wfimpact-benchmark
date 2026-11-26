#!/usr/bin/env bash
# Extract the process summary and the provenance graph of the baseline run.
#
# Usage (on IFB, from anywhere):
#     bash setup_baseline.sh                 # rnaseq, uses ~/rnaseq_test
#     PIPE=ampliseq bash setup_baseline.sh   # ampliseq, uses ~/ampliseq_test
#     BASE=/path/to/run bash setup_baseline.sh
# The container path is part of every task hash: keep it identical across runs
export NXF_SINGULARITY_CACHEDIR="${NXF_SINGULARITY_CACHEDIR:-$HOME/singularity_cache}"
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PIPE="${PIPE:-rnaseq}"
source "$HERE/pipelines/$PIPE.env"
TRACE="$(ls -t "$BASE"/results/pipeline_info/execution_trace_*.txt | head -1)"

python3 "$HERE/trace2proc.py" "$TRACE" -o "${BL}_trace.json"
python3 "$HERE/taskgraph.py" "$TRACE" -w "$BASE/work" -o "${BL}_provgraph.json"
echo "Baseline session id: $(awk -F'\t' '$4 == "OK" && $7 !~ /-preview/ && $7 !~ /-resume/ { s = $6 } END { print s }' "$BASE/.nextflow/history")"
