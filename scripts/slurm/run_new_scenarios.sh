#!/usr/bin/env bash
#SBATCH -A adaptprov
#SBATCH -J new_scen
#SBATCH -c 2
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH -o /path/to/home/wfimpact/runs/run_new_%j.log
# Run the new scenarios (R12, R13 on rnaseq, A10-A12 on ampliseq) one after
# the other, each with -resume from its baseline, then delete the task
# directories that are new and the published results except pipeline_info.
module load nextflow singularity openjdk
export NXF_SINGULARITY_CACHEDIR=$HOME/singularity_cache
cd ~/wfimpact

cleanup() {   # $1 = run directory, $2 = baseline launch directory
    local T BT
    BT=$(ls -t "$2"/results/pipeline_info/execution_trace_*.txt | head -1)
    T=$(ls -t "$1"/results/pipeline_info/execution_trace_*.txt 2>/dev/null | head -1)
    [ -n "$T" ] || return 0
    comm -13 <(cut -f2 "$BT" | sort -u) \
             <(awk -F'\t' 'NR==1{for(i=1;i<=NF;i++){if($i=="hash")h=i; if($i=="status")s=i}} NR>1 && $s!="CACHED"{print $h}' "$T" | sort -u) |
    while read -r hh; do [ -n "$hh" ] && rm -rf "$2"/work/${hh}*; done
    find "$1/results" -mindepth 1 -maxdepth 1 ! -name pipeline_info -exec rm -rf {} +
    rm -rf /shared/projects/adaptprov/tmp/t_*
}

run() {   # $1 = pipeline, $2 = scenario, $3 = baseline launch directory
    echo "=== $1 $2  $(date)"
    if [ -e runs/$2 ]; then echo "runs/$2 exists, skipped"; return; fi
    PIPE=$1 BASE=$3 bash run_scenario.sh scenarios/$1/$2.yaml || echo "run_scenario.sh exited with $? for $2"
    [ -f runs/$2/ground_truth.json ] && python3 -c "import json,sys;g=json.load(open(sys.argv[1]));print({k:len(v) for k,v in g.items()})" runs/$2/ground_truth.json
    cleanup runs/$2 "$3"
}

# rnaseq: baseline in the home directory, session read from its history
unset SESSION
for S in R12_salmon_libtype_auto R13_trim_quality_30; do
    run rnaseq $S $HOME/rnaseq_test
done

# ampliseq: baseline in project space, resumed baseline, so the session is given
export SESSION=dffe06d0-34fe-4828-9ace-f78ec57e5b39
for S in A12_silva A11_picrust A10_kraken2; do
    run ampliseq $S /shared/projects/adaptprov/ampliseq_base
done
echo "=== all done $(date)"
