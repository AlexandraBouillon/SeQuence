"""MUERP Algorithms 1–4 and the paper’s two baselines (analytic Eq. (1)–(2))."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import networkx as nx


@dataclass
class Channel:
    src: int
    dst: int
    path: list[int]
    rate: float

    @property
    def switches(self) -> list[int]:
        return [node for node in self.path[1:-1]]


class UnionFind:
    def __init__(self, items: list[int]):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)

    def n_components(self, items: list[int]) -> int:
        return len({self.find(x) for x in items})


def consume(q_left: dict[int, int], channel: Channel, switches: set[int]) -> None:
    for node in channel.switches:
        if node in switches:
            q_left[node] -= 2


def feasible(q_left: dict[int, int], channel: Channel, switches: set[int]) -> bool:
    need: dict[int, int] = {}
    for node in channel.switches:
        if node in switches:
            need[node] = need.get(node, 0) + 2
    return all(q_left.get(node, 0) >= extra for node, extra in need.items())


def algorithm1(
    graph: nx.Graph,
    src: int,
    dst: int,
    switches: set[int],
    q_left: dict[int, int],
    alpha: float,
    q_swap: float,
) -> Channel | None:
    """Maximum-rate channel: Dijkstra on weights αL − ln q (Zeng et al., Alg. 1)."""
    if src == dst:
        return None
    inf = float("inf")
    dist = {node: inf for node in graph.nodes}
    dist[src] = 0.0
    prev: dict[int, int] = {}
    heap = [(0.0, src)]
    visited: set[int] = set()
    minus_ln_q = -math.log(q_swap)
    while heap:
        d_u, uk = heapq.heappop(heap)
        if uk in visited:
            continue
        visited.add(uk)
        if d_u == inf:
            break
        if uk == dst:
            break
        for uh in graph.neighbors(uk):
            if uh in switches and q_left.get(uh, 0) < 2:
                continue
            weight = alpha * graph[uk][uh]["length"] + minus_ln_q
            nd = d_u + weight
            if nd < dist[uh]:
                dist[uh] = nd
                prev[uh] = uk
                heapq.heappush(heap, (nd, uh))
    if dst not in prev:
        return None
    path = [dst]
    pos = dst
    while pos != src:
        pos = prev[pos]
        path.append(pos)
    path.reverse()
    rate = math.exp(-math.log(q_swap) - dist[dst])
    if rate <= 0:
        return None
    return Channel(src, dst, path, rate)


def all_pair_channels(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    q_left: dict[int, int],
    alpha: float,
    q_swap: float,
) -> list[Channel]:
    channels: list[Channel] = []
    for i, ui in enumerate(users):
        for uj in users[i + 1 :]:
            ch = algorithm1(graph, ui, uj, switches, q_left, alpha, q_swap)
            if ch is not None:
                channels.append(ch)
    channels.sort(key=lambda c: -c.rate)
    return channels


def _product(channels: list[Channel]) -> float:
    if not channels:
        return 0.0
    rate = 1.0
    for ch in channels:
        rate *= ch.rate
    return rate


def algorithm2(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    alpha: float,
    q_swap: float,
) -> tuple[list[Channel], float]:
    """Optimal when Q_r ≥ 2|U| (capacity ignored in Alg. 1)."""
    q_inf = {s: 10**9 for s in switches}
    channels = all_pair_channels(graph, users, switches, q_inf, alpha, q_swap)
    uf = UnionFind(users)
    chosen: list[Channel] = []
    for ch in channels:
        if uf.union(ch.src, ch.dst):
            chosen.append(ch)
        if uf.n_components(users) == 1:
            break
    if uf.n_components(users) != 1:
        return [], 0.0
    return chosen, _product(chosen)


def _reconnect(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    q_left: dict[int, int],
    uf: UnionFind,
    alpha: float,
    q_swap: float,
    chosen: list[Channel],
) -> bool:
    while uf.n_components(users) > 1:
        best: Channel | None = None
        for i, ui in enumerate(users):
            for uj in users[i + 1 :]:
                if uf.connected(ui, uj):
                    continue
                ch = algorithm1(graph, ui, uj, switches, q_left, alpha, q_swap)
                if ch is None or not feasible(q_left, ch, switches):
                    continue
                if best is None or ch.rate > best.rate:
                    best = ch
        if best is None:
            return False
        consume(q_left, best, switches)
        uf.union(best.src, best.dst)
        chosen.append(best)
    return True


def algorithm3(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    q_cap: int,
    alpha: float,
    q_swap: float,
) -> tuple[list[Channel], float]:
    """Conflict-free heuristic from Alg. 2’s candidate channels."""
    q_left = {s: q_cap for s in switches}
    _, _ = algorithm2(graph, users, switches, alpha, q_swap)
    q_inf = {s: 10**9 for s in switches}
    candidates = all_pair_channels(graph, users, switches, q_inf, alpha, q_swap)
    uf = UnionFind(users)
    chosen: list[Channel] = []
    for ch in candidates:
        if not feasible(q_left, ch, switches):
            continue
        if uf.union(ch.src, ch.dst):
            consume(q_left, ch, switches)
            chosen.append(ch)
    if not _reconnect(graph, users, switches, q_left, uf, alpha, q_swap, chosen):
        return [], 0.0
    return chosen, _product(chosen)


def algorithm4(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    q_cap: int,
    alpha: float,
    q_swap: float,
    rng_start: int | None = None,
) -> tuple[list[Channel], float]:
    """Prim-based heuristic."""
    q_left = {s: q_cap for s in switches}
    u0 = users[0] if rng_start is None else users[rng_start % len(users)]
    in_set = {u0}
    out_set = set(users) - in_set
    chosen: list[Channel] = []
    while out_set:
        best: Channel | None = None
        for ui in in_set:
            for uj in out_set:
                ch = algorithm1(graph, ui, uj, switches, q_left, alpha, q_swap)
                if ch is None or not feasible(q_left, ch, switches):
                    continue
                if best is None or ch.rate > best.rate:
                    best = ch
        if best is None:
            return [], 0.0
        consume(q_left, best, switches)
        chosen.append(best)
        new_user = best.dst if best.dst in out_set else best.src
        in_set.add(new_user)
        out_set.remove(new_user)
    return chosen, _product(chosen)


def e_qcast(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    q_cap: int,
    alpha: float,
    q_swap: float,
) -> tuple[list[Channel], float]:
    """Path of consecutive user pairs (paper’s E-Q-CAST extension)."""
    q_left = {s: q_cap for s in switches}
    chosen: list[Channel] = []
    ordered = list(users)
    for ui, uj in zip(ordered[:-1], ordered[1:]):
        ch = algorithm1(graph, ui, uj, switches, q_left, alpha, q_swap)
        if ch is None or not feasible(q_left, ch, switches):
            return [], 0.0
        consume(q_left, ch, switches)
        chosen.append(ch)
    return chosen, _product(chosen)


def n_fusion(
    graph: nx.Graph,
    users: list[int],
    switches: set[int],
    q_cap: int,
    alpha: float,
    q_swap: float,
) -> tuple[list[Channel], float]:
    """Star through a central user (N-FUSION / MP-P with finite Q)."""
    best_rate = 0.0
    best_tree: list[Channel] = []
    for hub in users:
        q_left = {s: q_cap for s in switches}
        chosen: list[Channel] = []
        ok = True
        for other in users:
            if other == hub:
                continue
            ch = algorithm1(graph, hub, other, switches, q_left, alpha, q_swap)
            if ch is None or not feasible(q_left, ch, switches):
                ok = False
                break
            consume(q_left, ch, switches)
            chosen.append(ch)
        if not ok:
            continue
        rate = _product(chosen)
        if rate > best_rate:
            best_rate = rate
            best_tree = chosen
    return best_tree, best_rate


SOLVERS = {
    "alg2": lambda g, u, s, qcap, a, q: algorithm2(g, u, s, a, q),
    "alg3": algorithm3,
    "alg4": algorithm4,
    "e_qcast": e_qcast,
    "n_fusion": n_fusion,
}
