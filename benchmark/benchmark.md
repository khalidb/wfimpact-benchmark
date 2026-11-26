# Benchmark of adaptation requests

26 requests on nf-core/rnaseq 3.28.0 and nf-core/ampliseq 3.1.0, run with the `test` profile. Ground truth from execution with `-resume` on the baseline run. F1 is the micro-average over added, removed and affected processes. LLMs: Claude Opus 5.5 and GPT-6.2, both at medium effort through their web interfaces. The hybrid column uses Claude. Infeasible requests have no ground truth.

| Pipeline | Name | Kind | Phrasing | Request | Configuration change | Feasibility | Add | Rem | Aff | F1 struct. | F1 Claude | F1 GPT | F1 hybrid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rnaseq | Hisat2 | Tool substitution | explicit | Our machine has little memory. Please use HISAT2 rather than STAR for the alignment. | aligner: hisat2 | feasible | 8 | 13 | 28 | 1.0 | 1.0 | 1.0 | 1.0 |
| rnaseq | Rsem | Tool substitution | explicit | We would like the gene quantification to be done with RSEM. | aligner: star_rsem | feasible | 8 | 6 | 34 | 0.48 | 1.0 | 0.94 | 1.0 |
| rnaseq | Fastp | Tool substitution | explicit | Please use fastp for adapter and quality trimming. | trimmer: fastp | feasible | 3 | 2 | 52 | 1.0 | 1.0 | 1.0 | 1.0 |
| rnaseq | Kallisto | Tool substitution | explicit | We would prefer Kallisto rather than Salmon for the pseudo-alignment quantification. | pseudo_aligner: kallisto | rejected |  |  |  |  |  |  |  |
| rnaseq | NoTrim | Step removal | need | Our reads have already been trimmed by the sequencing facility, so there is no need to trim them again. | skip_trimming | feasible | 0 | 2 | 51 | 1.0 | 1.0 | 0.98 | 1.0 |
| rnaseq | NoMarkDup | Step removal | explicit | We do not want duplicate reads to be marked. | skip_markduplicates | feasible | 0 | 5 | 23 | 1.0 | 1.0 | 1.0 | 1.0 |
| rnaseq | NoQC | Step removal | need | We are short of time. Please skip the quality control steps. | skip_qc | feasible | 0 | 16 | 1 | 0.97 | 1.0 | 1.0 | 1.0 |
| rnaseq | RiboRemoval | Step addition | explicit | Our libraries contain a lot of ribosomal RNA. Please remove the rRNA reads before alignment. | remove_ribo_rna | feasible | 4 | 0 | 49 | 0.14 | 1.0 | 0.98 | 1.0 |
| rnaseq | Umi | Step addition | need | Our libraries contain unique molecular identifiers (UMIs), with the barcode in the first four bases of each read. Please take them into account. | with_umi | feasible | 18 | 5 | 48 | 0.79 | 1.0 | 0.99 | 1.0 |
| rnaseq | NoSpikeIn | Reference data | need | We did not add the GFP spike-in to our samples, so please do not include it in the reference. | additional_fasta: null | feasible | 0 | 2 | 55 | 1.0 | 1.0 | 1.0 | 1.0 |
| rnaseq | Gencode | Reference data | need | Our annotation file comes from GENCODE. | gencode | feasible | 1 | 2 | 54 | 0.03 | 1.0 | 0.95 | 1.0 |
| rnaseq | LibType | Analysis setting | need | We are unsure about the strandedness recorded for our samples. Please have the quantification infer the library type from the reads themselves instead. | salmon_quant_libtype: A | feasible | 0 | 0 | 13 | 0.0 | 1.0 | 1.0 | 1.0 |
| rnaseq | Trim30 | Analysis setting | explicit | Please trim low-quality bases more stringently, with a Phred quality cut-off of 30 in Trim Galore. | extra_trimgalore_args: --quality 30 | feasible | 0 | 0 | 53 | 0.0 | 1.0 | 0.98 | 1.0 |
| ampliseq | Kraken2 | Tool substitution | explicit | Please assign taxonomy with Kraken2 and the Greengenes database instead of DADA2. | skip_dada_taxonomy: true, kraken2_ref_taxonomy: greengenes | feasible | 3 | 4 | 34 | 0.33 | 1.0 | 1.0 | 1.0 |
| ampliseq | NoQiime | Step removal | need | We cannot use QIIME2 on our infrastructure. | skip_qiime | feasible | 0 | 41 | 4 | 0.97 | 1.0 | 1.0 | 1.0 |
| ampliseq | NoDiffAbund | Step removal | need | I am in a hurry and do not need any differential abundance testing. | four options off | feasible | 0 | 9 | 2 | 0.95 | 1.0 | 1.0 | 1.0 |
| ampliseq | NoDecontam | Step removal | need | We did not sequence any negative controls in this run. | decontam: none | feasible | 0 | 2 | 53 | 0.96 | 0.98 | 1.0 | 1.0 |
| ampliseq | SkipQualProfile | Step removal | explicit | We have already checked read quality ourselves, so please skip the DADA2 quality profiling. | skip_dada_quality | rejected |  |  |  |  |  |  |  |
| ampliseq | Picrust | Step addition | need | We would also like an estimate of the metabolic functions that our communities may carry. | picrust: true | feasible | 1 | 0 | 2 | 0.5 | 1.0 | 1.0 | 1.0 |
| ampliseq | Silva | Reference data | need | Our group reports taxonomy against SILVA 138 rather than GTDB. Please classify the sequences with that reference. | dada_ref_taxonomy: silva=138 | feasible | 0 | 0 | 40 | 0.0 | 1.0 | 0.93 | 1.0 |
| ampliseq | Pooled | Analysis setting | need | Many of our taxa are rare and spread thinly across samples. Please let the denoising use the information from all samples together. | sample_inference: pooled | feasible | 0 | 0 | 64 | 0.0 | 1.0 | 0.98 | 1.0 |
| ampliseq | Rarefy1000 | Analysis setting | explicit | For the diversity analyses, please rarefy to at least 1,000 reads per sample. | rarefaction_depth: 1000 | fails at run time |  |  |  |  |  |  |  |
| ampliseq | Rarefy600 | Analysis setting | explicit | For the diversity analyses, please rarefy to at least 600 reads per sample, even if the shallowest samples have to be left out. | rarefaction_depth: 600 | feasible | 0 | 0 | 7 | 0.0 | 1.0 | 1.0 | 1.0 |
| ampliseq | NoArchaea | Analysis setting | need | We are only interested in bacteria. Please also remove archaeal ASVs, in addition to mitochondria and chloroplasts. | exclude_taxa | feasible | 0 | 0 | 33 | 0.0 | 1.0 | 1.0 | 1.0 |
| ampliseq | MinFreq5 | Analysis setting | explicit | Please keep rarer ASVs: only remove those with fewer than five reads in total. | min_frequency: 5 | feasible | 0 | 0 | 33 | 0.0 | 1.0 | 1.0 | 1.0 |
| ampliseq | Truncate | Analysis setting | explicit | Please truncate forward reads at 230 bases and reverse reads at 180 bases. | trunclenf/r | feasible | 0 | 1 | 67 | 0.03 | 0.99 | 0.98 | 1.0 |
