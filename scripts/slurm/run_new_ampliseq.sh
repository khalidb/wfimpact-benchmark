#!/usr/bin/env bash
#SBATCH -A adaptprov
#SBATCH -J new_ampli
#SBATCH -c 2
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH -o /path/to/home/wfimpact/runs/run_new_ampliseq_%j.log
# Rerun A12 and A11 on ampliseq (A10 is valid). Submit from a LOGIN node, not from an
# interactive srun session, so that the job does not inherit that session's
# temporary directory.
module load nextflow singularity openjdk
export NXF_SINGULARITY_CACHEDIR=$HOME/singularity_cache
export TMPDIR=/shared/projects/adaptprov/tmp/nxf_head_${SLURM_JOB_ID}
export NXF_TEMP=$TMPDIR
mkdir -p "$TMPDIR"
export SESSION=dffe06d0-34fe-4828-9ace-f78ec57e5b39
export PIPE=ampliseq
BASE=/shared/projects/adaptprov/ampliseq_base
BT=$(ls -t $BASE/results/pipeline_info/execution_trace_*.txt | head -1)
cd ~/wfimpact

cleanup() {   # $1 = run directory: delete task directories not in the baseline
    local T
    T=$(ls -t "$1"/results/pipeline_info/execution_trace_*.txt 2>/dev/null | head -1)
    [ -n "$T" ] || return 0
    comm -13 <(cut -f2 "$BT" | sort -u) \
             <(awk -F'\t' 'NR==1{for(i=1;i<=NF;i++){if($i=="hash")h=i; if($i=="status")s=i}} NR>1 && $s!="CACHED"{print $h}' "$T" | sort -u) |
    while read -r hh; do [ -n "$hh" ] && rm -rf "$BASE"/work/${hh}*; done
    find "$1/results" -mindepth 1 -maxdepth 1 ! -name pipeline_info -exec rm -rf {} +
    # only old temporary directories, so that tasks of other running jobs keep theirs
    find /shared/projects/adaptprov/tmp -maxdepth 1 -name "t_*" -mmin +720 -exec rm -rf {} +
}

# Remove the traces of the failed attempts, including task directories that
# the interrupted A11 run may have left behind (they would be wrongly reused).
SCEN="${SCEN:-A12_silva A11_picrust}"
for S in $SCEN; do
    [ -e runs/$S ] && { cleanup runs/$S; mv runs/$S runs/${S}_failed_tmpdir_$(date +%s); }
done

for S in $SCEN; do
    echo "=== $S  $(date)"
    bash run_scenario.sh scenarios/ampliseq/$S.yaml || echo "run_scenario.sh exited with $? for $S"
    [ -f runs/$S/ground_truth.json ] && python3 -c "import json,sys;g=json.load(open(sys.argv[1]));print({k:len(v) for k,v in g.items()})" runs/$S/ground_truth.json
    echo "exit status: $(cat runs/$S/nextflow_exit_status.txt 2>/dev/null)"
    cleanup runs/$S
done
rm -rf "$TMPDIR"
echo "=== all done $(date)"
