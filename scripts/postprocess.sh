#!/usr/bin/env bash
# Rebuild trace.json, provgraph.json and ground_truth.json for a scenario that
# has already run (for instance when Nextflow stopped on a late error).
# Usage: bash postprocess.sh runs/R03_fastp
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PIPE="${PIPE:-rnaseq}"
source "$HERE/pipelines/$PIPE.env"
cd "$1"
TRACE="$(ls -t results/pipeline_info/execution_trace_*.txt | head -1)"
python3 "$HERE/trace2proc.py" "$TRACE" -o trace.json
python3 "$HERE/taskgraph.py" "$TRACE" -w "$BASE/work" -o provgraph.json
echo "Ground truth for $(basename "$PWD"):"
python3 "$HERE/compare.py" trace "${BL}_trace.json" trace.json -o ground_truth.json
