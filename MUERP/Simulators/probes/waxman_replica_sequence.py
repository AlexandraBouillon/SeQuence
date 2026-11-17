"""One Sec. V-A-scale Waxman replica on SeQUeNCe (admission + analytic P).

Not Algorithms 1-4. Tree = MST of shortest-path distances among 10 users.
Records load/init/RSVP wall-clock, RSS, occupancy, and Eq. (2) if every
tree channel is admitted, else P = 0.
"""

from __future__ import annotations

import json
import resource
import sys
import time
from math import dist, exp, log
from pathlib import Path

import networkx as nx
import sequence as sq
from sequence.constants import SECOND, SINGLE_HERALDED
from sequence.utils.nx_converter import generate_config, router_name_func

HERE = Path(__file__).resolve().parent
N_USERS = 10
N_SWITCHES = 50
N_NODES = N_USERS + N_SWITCHES
TARGET_DEGREE = 6
AREA = 10_000.0
ALPHA_PAPER = 1e-4
Q_SWAP = 0.9
Q_R = 4
USER_MEMORIES = 32
SEED = 0
# Paper p = exp(-α L_km). SeQUeNCe loss is 10^(-att_dB_m * L_m / 10).
ATT_DB_PER_M = ALPHA_PAPER / (100.0 * log(10.0))


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)


def build_connected_waxman(n: int, area: float, seed: int) -> tuple[nx.Graph, dict]:
    best = None
    for alpha in (0.1, 0.15, 0.2, 0.25, 0.3):
        for beta in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0):
            graph = nx.waxman_graph(
                n, alpha=alpha, beta=beta, domain=(0, 0, area, area), seed=seed
            )
            if not nx.is_connected(graph):
                continue
            degree = 2 * graph.number_of_edges() / n
            meta = {"alpha": alpha, "beta": beta, "degree": degree, "edges": graph.number_of_edges()}
            if best is None or abs(degree - TARGET_DEGREE) < abs(best[1]["degree"] - TARGET_DEGREE):
                best = (graph, meta)
            if abs(degree - TARGET_DEGREE) <= 0.5:
                return graph, meta
    if best is None:
        raise RuntimeError("no connected Waxman graph found")
    return best


def attach_lengths(graph: nx.Graph) -> None:
    for node in graph.nodes:
        graph.nodes[node]["node_type"] = "processing"
    for u, v in graph.edges:
        graph[u][v]["length"] = dist(graph.nodes[u]["pos"], graph.nodes[v]["pos"])
        graph[u][v]["attenuation"] = ATT_DB_PER_M


def user_mst_channels(graph: nx.Graph, users: list, name_of) -> list[tuple[str, str, list[str]]]:
    """Spanning tree on users; each tree edge is a shortest path in G. Not Algs 1-4."""
    complete = nx.Graph()
    for a in users:
        for b in users:
            if a >= b:
                continue
            length = nx.shortest_path_length(graph, a, b, weight="length")
            complete.add_edge(a, b, weight=length)
    tree = nx.minimum_spanning_tree(complete, weight="weight")
    channels = []
    for a, b in tree.edges:
        path_nodes = nx.shortest_path(graph, a, b, weight="length")
        path_names = [name_of[n] for n in path_nodes]
        channels.append((name_of[a], name_of[b], path_names))
    return channels


def channel_rate(graph: nx.Graph, path_nodes: list, name_to_graph: dict, q: float) -> float:
    hops = len(path_nodes) - 1
    p_prod = 1.0
    for left, right in zip(path_nodes[:-1], path_nodes[1:]):
        u, v = name_to_graph[left], name_to_graph[right]
        length_km = graph[u][v]["length"]
        p_prod *= exp(-ALPHA_PAPER * length_km)
    return (q ** (hops - 1)) * p_prod if hops >= 1 else 0.0


def occupancy(network_topo: sq.RouterNetTopo, switch_names: set[str]) -> dict:
    used = {}
    for node in network_topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER):
        if node.name not in switch_names:
            continue
        n = sum(1 for card in node.network_manager.get_timecards() if card.reservations)
        used[node.name] = n
    return used


def main() -> int:
    t0 = time.perf_counter()
    graph, waxman_meta = build_connected_waxman(N_NODES, AREA, SEED)
    attach_lengths(graph)
    users = list(range(N_USERS))
    name_of = {node: router_name_func(i) for i, node in enumerate(graph.nodes)}
    name_to_graph = {v: k for k, v in name_of.items()}
    switch_names = {name_of[n] for n in graph.nodes if n not in users}

    config, _ = generate_config(
        graph,
        cc_delay=1,
        memory_size=USER_MEMORIES,
        output_file="",
        output_directory="",
        stop_time=0.1,
        formalism="bell_diagonal",
    )
    config["templates"]["router_template"]["EntanglementSwapping"] = {
        "swapping_success_prob": Q_SWAP,
    }
    user_names = {name_of[u] for u in users}
    for node in config["nodes"]:
        if node.get("type") != "QuantumRouter":
            continue
        node["memo_size"] = USER_MEMORIES if node["name"] in user_names else Q_R

    json_path = HERE / "waxman_replica.json"
    json_path.write_text(json.dumps({"meta": waxman_meta, "n_nodes": N_NODES}))
    t_graph = time.perf_counter()

    sq.EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    network_topo = sq.RouterNetTopo(config)
    timeline = network_topo.get_timeline()
    timeline.show_progress = False
    t_load = time.perf_counter()

    routers = {
        node.name: node
        for node in network_topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)
    }
    for name in user_names:
        sq.RequestApp(routers[name])
        routers[name].swapping_success_prob = Q_SWAP
    for name in switch_names:
        routers[name].swapping_success_prob = Q_SWAP

    channels = user_mst_channels(graph, users, name_of)
    timeline.init()
    t_init = time.perf_counter()
    for src, dst, _path in channels:
        routers[src].app.start(
            responder=dst,
            start_t=1 * SECOND,
            end_t=2 * SECOND,
            memo_size=1,
            fidelity=0.5,
        )
    timeline.run()
    t_run = time.perf_counter()

    accepted = []
    for name in list(user_names) + list(switch_names):
        accepted.extend(routers[name].network_manager.rsvp.accepted_reservations)
    uniq = {(res.initiator, res.responder): res for res in accepted}
    admitted = []
    rates = []
    for src, dst, path_names in channels:
        ok = (src, dst) in uniq or (dst, src) in uniq
        admitted.append(ok)
        rates.append(channel_rate(graph, path_names, name_to_graph, Q_SWAP) if ok else 0.0)

    tree_ok = all(admitted)
    p_tree = 0.0 if not tree_ok else 1.0
    if tree_ok:
        for rate in rates:
            p_tree *= rate

    occ = occupancy(network_topo, switch_names)
    result = {
        "waxman": waxman_meta,
        "n_users": N_USERS,
        "n_switches": N_SWITCHES,
        "q_r": Q_R,
        "q": Q_SWAP,
        "alpha_paper": ALPHA_PAPER,
        "n_qchannels": len(config.get("qchannels", [])),
        "n_bsm": sum(1 for n in config["nodes"] if n.get("type") == "BSMNode"),
        "n_tree_channels": len(channels),
        "admitted": dict(zip([f"{s}-{d}" for s, d, _ in channels], admitted)),
        "n_admitted": sum(admitted),
        "P": p_tree,
        "switch_memories_used_max": max(occ.values()) if occ else 0,
        "switch_memories_used_sum": sum(occ.values()),
        "switches_saturated": sum(1 for v in occ.values() if v >= Q_R),
        "seconds": {
            "graph_config": t_graph - t0,
            "load_topo": t_load - t_graph,
            "init": t_init - t_load,
            "rsvp_run": t_run - t_init,
            "total": t_run - t0,
        },
        "peak_rss_mb": rss_mb(),
        "note": "Dummy MST of shortest paths, not paper Algorithms 1-4. Admission-only.",
    }
    out = HERE / "waxman_replica_sequence_results.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
