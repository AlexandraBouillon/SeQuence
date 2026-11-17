"""Random topologies for the MUERP Sec. V-A setup."""

from __future__ import annotations

from math import dist

import networkx as nx
import numpy as np


def _place(n: int, area: float, rng: np.random.Generator) -> dict:
    pos = {i: (float(rng.uniform(0, area)), float(rng.uniform(0, area))) for i in range(n)}
    return pos


def _set_lengths(graph: nx.Graph, pos: dict) -> nx.Graph:
    for u, v in graph.edges:
        graph[u][v]["length"] = dist(pos[u], pos[v])
    nx.set_node_attributes(graph, pos, "pos")
    return graph


def _force_connected(graph: nx.Graph, pos: dict) -> nx.Graph:
    if nx.is_connected(graph):
        return graph
    components = [list(c) for c in nx.connected_components(graph)]
    for left, right in zip(components[:-1], components[1:]):
        u, v = min(
            ((a, b) for a in left for b in right),
            key=lambda ab: dist(pos[ab[0]], pos[ab[1]]),
        )
        graph.add_edge(u, v)
    return graph


def _match_edge_count(graph: nx.Graph, pos: dict, n_edges: int, rng: np.random.Generator) -> nx.Graph:
    graph = graph.copy()
    while graph.number_of_edges() > n_edges and nx.is_connected(graph):
        bridges = set(nx.bridges(graph))
        candidates = [e for e in graph.edges if e not in bridges and (e[1], e[0]) not in bridges]
        if not candidates:
            break
        u, v = candidates[int(rng.integers(0, len(candidates)))]
        graph.remove_edge(u, v)
    nodes = list(graph.nodes)
    guard = 0
    while graph.number_of_edges() < n_edges and guard < n_edges * 20:
        guard += 1
        u, v = int(rng.choice(nodes)), int(rng.choice(nodes))
        if u != v and not graph.has_edge(u, v):
            graph.add_edge(u, v)
    return _force_connected(graph, pos)


def split_users_switches(n_users: int, n_switches: int) -> tuple[list[int], list[int]]:
    users = list(range(n_users))
    switches = list(range(n_users, n_users + n_switches))
    return users, switches


def build_waxman(n: int, area: float, n_edges: int, rng: np.random.Generator) -> nx.Graph:
    seed = int(rng.integers(0, 10**9))
    pos = _place(n, area, rng)
    best = None
    for alpha in (0.1, 0.2, 0.3, 0.4):
        for beta in (0.2, 0.4, 0.6, 0.8, 1.0):
            g = nx.waxman_graph(
                n, alpha=alpha, beta=beta, domain=(0, 0, area, area), seed=seed
            )
            g = nx.convert_node_labels_to_integers(g)
            if best is None or abs(g.number_of_edges() - n_edges) < abs(
                best.number_of_edges() - n_edges
            ):
                best = g
    graph = best if best is not None else nx.gnm_random_graph(n, n_edges, seed=seed)
    if all("pos" in graph.nodes[i] for i in graph.nodes):
        pos = {i: tuple(graph.nodes[i]["pos"]) for i in graph.nodes}
    graph = _match_edge_count(graph, pos, n_edges, rng)
    return _set_lengths(graph, pos)


def build_watts_strogatz(n: int, area: float, n_edges: int, rng: np.random.Generator) -> nx.Graph:
    k = max(2, 2 * (2 * n_edges // n // 2))
    if k >= n:
        k = n - 1 if (n - 1) % 2 == 0 else n - 2
    k = max(2, k)
    graph = nx.watts_strogatz_graph(n, k, 0.3, seed=int(rng.integers(0, 10**9)))
    pos = _place(n, area, rng)
    graph = _match_edge_count(graph, pos, n_edges, rng)
    return _set_lengths(graph, pos)


def build_volchenkov(n: int, area: float, n_edges: int, rng: np.random.Generator) -> nx.Graph:
    """Scale-free stand-in (BA) for Volchenkov–Blanchard; nodes then placed in the area."""
    m = max(1, n_edges // n)
    graph = nx.barabasi_albert_graph(n, min(m, n - 1), seed=int(rng.integers(0, 10**9)))
    pos = _place(n, area, rng)
    graph = _match_edge_count(graph, pos, n_edges, rng)
    return _set_lengths(graph, pos)


GENERATORS = {
    "waxman": build_waxman,
    "watts_strogatz": build_watts_strogatz,
    "volchenkov": build_volchenkov,
}


def make_instance(
    kind: str,
    n_users: int,
    n_switches: int,
    degree: float,
    area: float,
    seed: int,
) -> tuple[nx.Graph, list[int], list[int]]:
    n = n_users + n_switches
    n_edges = max(n - 1, int(round(degree * n / 2)))
    rng = np.random.default_rng(seed)
    graph = GENERATORS[kind](n, area, n_edges, rng)
    users, switches = split_users_switches(n_users, n_switches)
    return graph, users, switches
