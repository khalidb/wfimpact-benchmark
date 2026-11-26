#!/usr/bin/env bash
#SBATCH -A adaptprov
#SBATCH -J ampliseq_scen
#SBATCH -c 2
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH -o /path/to/home/wfimpact/runs/run_all_%j.log
# Run the remaining ampliseq scenarios one after the other, each with -resume
# from the baseline, then delete only the task directories that are new
# (not in the baseline trace) and the published results except pipeline_info.
module load nextflow singularity openjdk
export NXF_SINGULARITY_CACHEDIR=$HOME/singularity_cache
export SESSION=dffe06d0-34fe-4828-9ace-f78ec57e5b39
export PIPE=ampliseq
BASE=/shared/projects/adaptprov/ampliseq_base
BT=$(ls -t $BASE/results/pipeline_info/execution_trace_*.txt | head -1)
cd ~/wfimpact

cleanup() {   # $1 = run directory
    local T
    T=$(ls -t "$1"/results/pipeline_info/execution_trace_*.txt 2>/dev/null | head -1)
    [ -n "$T" ] || return 0
    comm -13 <(cut -f2 "$BT" | sort -u) \
             <(awk -F'\t' 'NR==1{for(i=1;i<=NF;i++){if($i=="hash")h=i; if($i=="status")s=i}} NR>1 && $s!="CACHED"{print $h}' "$T" | sort -u) |
    while read -r hh; do [ -n "$hh" ] && rm -rf "$BASE"/work/${hh}*; done
    find "$1/results" -mindepth 1 -maxdepth 1 ! -name pipeline_info -exec rm -rf {} +
    rm -rf /shared/projects/adaptprov/tmp/t_*
}

cleanup runs/A02a_rarefaction_1000

for S in A01_pooled A02b_rarefaction_600 A03_no_qiime A04_exclude_archaea \
         A05_min_frequency_5 A06_truncation A07_no_diff_abundance \
         A08_no_decontam A09a_skip_quality A09b_skip_quality_valid; do
    echo "=== $S  $(date)"
    if [ -e runs/$S ]; then echo "runs/$S exists, skipped"; continue; fi
    bash run_scenario.sh scenarios/ampliseq/$S.yaml || echo "run_scenario.sh exited with $? for $S"
    [ -f runs/$S/ground_truth.json ] && python3 -c "import json,sys;g=json.load(open(sys.argv[1]));print({k:len(v) for k,v in g.items()})" runs/$S/ground_truth.json
    cleanup runs/$S
    echo "files in project space: $(find $BASE | wc -l)"
done
echo "=== all done $(date)"
