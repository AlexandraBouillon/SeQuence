"""Eq. (1)–(2) from Zeng et al. SeQUeNCe has no native tree-rate metric.

P_A = q^{ℓ-1} ∏ p_{i,i+1},  p = exp(-α L),  P = ∏ P_A,  else 0.
"""

from __future__ import annotations

import math

import networkx as nx


def link_p(graph: nx.Graph, u, v, alpha: float) -> float:
    return math.exp(-alpha * float(graph[u][v]["length"]))


def channel_rate(graph: nx.Graph, path: list, q: float, alpha: float) -> float:
    if len(path) < 2:
        return 0.0
    n_edges = len(path) - 1
    prod = 1.0
    for a, b in zip(path[:-1], path[1:]):
        prod *= link_p(graph, a, b, alpha)
    return (q ** (n_edges - 1)) * prod


def tree_rate(graph: nx.Graph, paths: list[list], q: float, alpha: float, complete: bool) -> float:
    """Eq. (2). Incomplete or empty tree → 0."""
    if not complete or not paths:
        return 0.0
    rate = 1.0
    for path in paths:
        pa = channel_rate(graph, path, q, alpha)
        if pa <= 0:
            return 0.0
        rate *= pa
    return rate
