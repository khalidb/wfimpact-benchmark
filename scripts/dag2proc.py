#!/usr/bin/env python3
"""Reduce a Nextflow Mermaid DAG (HTML or .mmd) to a process-level graph.

Nextflow DAGs contain process nodes, channel nodes and operator nodes. This
script keeps process nodes only, identified by their fully qualified name
(e.g. NFCORE_RNASEQ:RNASEQ:ALIGN_STAR:STAR_ALIGN), and adds an edge P -> Q
whenever Q can be reached from P through channel and operator nodes only.

Caveat: the set of processes is reliable (it reflects the configuration,
since Nextflow resolves `if` blocks when building the DAG), but the edges are
only approximate. Shared channel nodes in Nextflow's rendering create paths
that do not correspond to dataflow. For dependency edges, prefer the graph
rebuilt from a run's work directory with taskgraph.py.

Usage:
    python3 dag2proc.py dag.html -o graph.json
"""
import argparse
import json
import re
import sys
from collections import defaultdict

SUBGRAPH = re.compile(r'^\s*subgraph\s+"([^"]*)"')
END = re.compile(r'^\s*end\s*$')
PROCESS = re.compile(r'^\s*(v\d+)\(\["([^"]+)"\]\)')
EDGE = re.compile(r'^\s*(v\d+)\s*-->\s*(v\d+)')


def parse(text):
    """Return (processes, edges): processes maps node id -> qualified name."""
    stack = []
    processes = {}
    edges = defaultdict(set)
    for line in text.splitlines():
        m = SUBGRAPH.match(line)
        if m:
            # Subgraph labels look like "NFCORE_RNASEQ:RNASEQ:ALIGN_STAR [ALIGN_STAR]"
            label = m.group(1).split(' [')[0].strip()
            stack.append(label)
            continue
        if END.match(line):
            if stack:
                stack.pop()
            continue
        m = PROCESS.match(line)
        if m:
            node, name = m.groups()
            scope = next((s for s in reversed(stack) if s), '')
            processes[node] = f'{scope}:{name}' if scope else name
            continue
        m = EDGE.match(line)
        if m:
            edges[m.group(1)].add(m.group(2))
    return processes, edges


def node_index(node):
    return int(node[1:])


def process_graph(processes, edges):
    """Collapse non-process nodes: keep P -> Q if Q is reachable via non-process nodes.

    Nextflow renders accumulator channels (e.g. files gathered for MultiQC, or
    sample status channels) as shared nodes, which creates cycles and paths
    that do not correspond to dataflow. Node ids follow the order in which the
    script creates them, and a consumer process is always invoked after its
    producers, so we only keep P -> Q when Q was created after P.
    """
    out = {}
    for src in processes:
        targets = set()
        seen = set()
        frontier = list(edges.get(src, ()))
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            if node in processes:
                if node_index(node) > node_index(src):
                    targets.add(processes[node])
            else:
                frontier.extend(edges.get(node, ()))
        out[processes[src]] = sorted(targets)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dag', help='Nextflow DAG in Mermaid format (.html or .mmd)')
    ap.add_argument('-o', '--output', help='output JSON file (default: stdout)')
    args = ap.parse_args()

    text = open(args.dag, encoding='utf-8').read()
    processes, edges = parse(text)
    if not processes:
        sys.exit('No process nodes found: is this a Mermaid DAG produced by Nextflow?')
    graph = process_graph(processes, edges)
    result = {
        'source': args.dag,
        'processes': sorted(graph),
        'edges': sorted([a, b] for a, bs in graph.items() for b in bs),
    }
    data = json.dumps(result, indent=2)
    if args.output:
        open(args.output, 'w').write(data + '\n')
        print(f'{len(result["processes"])} processes, {len(result["edges"])} edges -> {args.output}')
    else:
        print(data)


if __name__ == '__main__':
    main()
