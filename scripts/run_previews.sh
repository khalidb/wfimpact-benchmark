#!/usr/bin/env bash
# Generate the Nextflow DAG (preview, no task executed) for the baseline
# configuration and for every scenario, then reduce each DAG to its process set.
#
# Usage (on an IFB compute node, with the nextflow/singularity/openjdk modules loaded):
#     bash run_previews.sh [scenario_dir]
# The container path is part of every task hash: keep it identical across runs
export NXF_SINGULARITY_CACHEDIR="${NXF_SINGULARITY_CACHEDIR:-$HOME/singularity_cache}"
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PIPE="${PIPE:-rnaseq}"
source "$HERE/pipelines/$PIPE.env"
SCENARIOS="${1:-$SCEN_DIR}"
OUT="$PREV"
LAUNCH="${PREV}_launch"   # separate launch dir, so previews never touch the baseline run's history

mkdir -p "$OUT" "$LAUNCH"
cd "$LAUNCH"

preview () {
    local name="$1"; shift
    echo "== preview: $name"
    nextflow run "$PIPELINE" -r "$REVISION" -profile "$PROFILE" "$@" \
        --outdir "$LAUNCH/out_$name" -preview -with-dag "$OUT/$name.html" > "$OUT/$name.log" 2>&1 \
        || { echo "   failed, see $OUT/$name.log"; return 0; }
    python3 "$HERE/dag2proc.py" "$OUT/$name.html" -o "$OUT/$name.json"
}

preview baseline
for f in "$SCENARIOS"/*.yaml; do
    preview "$(basename "$f" .yaml)" -params-file "$f"
done

echo
echo "Process-set differences with the baseline:"
for f in "$OUT"/*.json; do
    name="$(basename "$f" .json)"
    case "$name" in baseline|*_vs_baseline) continue ;; esac
    echo "-- $name"
    python3 "$HERE/compare.py" graph "$OUT/baseline.json" "$f" -o "$OUT/${name}_vs_baseline.json" | sed 's/^/   /'
done
