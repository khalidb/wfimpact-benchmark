#!/usr/bin/env bash
#SBATCH -A adaptprov
#SBATCH -J rnaseq_rebase
#SBATCH -c 2
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH -o /path/to/home/wfimpact/runs/run_rnaseq_rebase_%j.log
# Rebuild the rnaseq baseline in project space, with the caching mode now set
# in ~/.nextflow/config (lenient), then rerun R12 and R13 against it.
# Submit from a LOGIN node.
module load nextflow singularity openjdk
export NXF_SINGULARITY_CACHEDIR=$HOME/singularity_cache
export TMPDIR=/shared/projects/adaptprov/tmp/nxf_head_${SLURM_JOB_ID}
export NXF_TEMP=$TMPDIR
mkdir -p "$TMPDIR"
export PIPE=rnaseq
BASE=/shared/projects/adaptprov/rnaseq_base
cd ~/wfimpact

# 1. Baseline
if [ ! -d "$BASE/results/pipeline_info" ]; then
    mkdir -p "$BASE" && cd "$BASE"
    nextflow run nf-core/rnaseq -r 3.28.0 -profile test,ifb_core --outdir "$BASE/results" \
        || { echo "baseline failed"; exit 1; }
    cd ~/wfimpact
fi
BT=$(ls -t $BASE/results/pipeline_info/execution_trace_*.txt | head -1)
echo "baseline tasks: $(($(wc -l < "$BT") - 1))"
# keep the old baseline summaries, write the new ones next to them
mkdir -p baseline_rnaseq_home && cp -n baseline_trace.json baseline_provgraph.json baseline_rnaseq_home/ 2>/dev/null
BASE=$BASE bash setup_baseline.sh

cleanup() {   # $1 = run directory: delete task directories not in the baseline
    local T
    T=$(ls -t "$1"/results/pipeline_info/execution_trace_*.txt 2>/dev/null | head -1)
    [ -n "$T" ] || return 0
    comm -13 <(cut -f2 "$BT" | sort -u) \
             <(awk -F'\t' 'NR==1{for(i=1;i<=NF;i++){if($i=="hash")h=i; if($i=="status")s=i}} NR>1 && $s!="CACHED"{print $h}' "$T" | sort -u) |
    while read -r hh; do [ -n "$hh" ] && rm -rf "$BASE"/work/${hh}*; done
    find "$1/results" -mindepth 1 -maxdepth 1 ! -name pipeline_info -exec rm -rf {} +
    rm -rf /shared/projects/adaptprov/tmp/t_*
}

# 2. Scenarios (the invalid first attempts are moved aside)
unset SESSION
for S in R12_salmon_libtype_auto R13_trim_quality_30; do
    [ -e runs/$S ] && mv runs/$S runs/${S}_invalid_cache_$(date +%s)
    echo "=== $S  $(date)"
    BASE=$BASE bash run_scenario.sh scenarios/rnaseq/$S.yaml || echo "run_scenario.sh exited with $? for $S"
    T=$(ls -t runs/$S/results/pipeline_info/execution_trace_*.txt | head -1)
    echo "task statuses:"; awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)if($i=="status")s=i} NR>1{print $s}' "$T" | sort | uniq -c
    [ -f runs/$S/ground_truth.json ] && python3 -c "import json,sys;g=json.load(open(sys.argv[1]));print({k:len(v) for k,v in g.items()})" runs/$S/ground_truth.json
    cleanup runs/$S
done
rm -rf "$TMPDIR"
echo "=== all done $(date)"
