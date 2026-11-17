"""SeQUeNCe kernel probes that the findings said were missing.

1. Algs 2–4 trees pinned into RSVP on one Waxman 10+50 graph.
2. Two MUERP groups sharing Q_r on that graph.
3. Slot P = Eq. (2) from admitted paths (SeQUeNCe has no native P).
4. Fidelity log on the Fig. 4a star (ES/DELIVERY events).
5. One-shot-ish EG window on that star (not a true simultaneous slot).

Not 20 replicas. Not a line-by-line Volchenkov–Blanchard generator.
Not a NetSquid column.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import sequence as sq
from sequence.constants import SECOND, SINGLE_HERALDED
from sequence.utils import metrics
from sequence.utils.graphs import build_star
from sequence.utils.metrics.builtins import (
    EG_METRIC,
    ES_METRIC,
    SWAPPED_FIDELITIES_METRIC,
    THROUGHPUT_METRIC,
)
from sequence.utils.metrics.event_types import EventTypes
from sequence.utils.nx_converter import default_template, generate_config, router_name_func

from .algorithms import SOLVERS, algorithm4
from .eq2 import tree_rate
from .graphs import make_instance

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ALPHA = 1e-4
Q_SWAP = 0.9
Q_R = 4
USER_MEM = 32
P_STAR = 0.9


def name_of(i: int) -> str:
    return router_name_func(i)


def int_of(name: str) -> int:
    return int(name.split("_")[1])


def configure_kernel() -> None:
    sq.EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    sq.EntanglementSwappingA.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)
    sq.EntanglementSwappingB.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)


def pin_path(routers: dict, path: list[str]) -> None:
    for seq in (path, list(reversed(path))):
        dest = seq[-1]
        for node, nxt in zip(seq[:-1], seq[1:]):
            routers[node].network_manager.get_routing_protocol().update_forwarding_rule(dest, nxt)


def assign_starts(tree_paths: list[list[str]]) -> list[dict]:
    used: set[str] = set()
    starts = []
    for path in tree_paths:
        src, dst = path[0], path[-1]
        oriented = path
        if src in used:
            src, dst = dst, src
            oriented = list(reversed(path))
        used.add(src)
        starts.append({"initiator": src, "responder": dst, "path": oriented})
    return starts


def occupancy(routers: dict, switches: list[str], q_r: int = Q_R) -> dict:
    max_occ, saturated, total = 0, 0, 0
    per = {}
    for name in switches:
        n = 0
        for card in routers[name].network_manager.get_timecards():
            if card.reservations:
                n += 1
        per[name] = n
        total += n
        max_occ = max(max_occ, n)
        if n >= q_r:
            saturated += 1
    return {"max": max_occ, "sum": total, "n_saturated": saturated}


def make_waxman_config(graph, users, switches, stop_s: float) -> dict:
    att = ALPHA / (100.0 * math.log(10.0))
    for u, v in graph.edges:
        graph[u][v]["attenuation"] = att
    template = {
        "router_template": {
            "MemoryArray": {
                "frequency": 200000000.0,
                "coherence_time": -1,
                "efficiency": 1,
                "fidelity": 0.9,
                "cutoff_flag": False,
            },
            "EntanglementSwapping": {"swapping_success_prob": Q_SWAP},
        },
        "bsm_template": default_template["bsm_template"],
    }
    config, _ = generate_config(
        graph,
        cc_delay=1,
        memory_size=USER_MEM,
        output_file="",
        output_directory="",
        stop_time=stop_s,
        formalism="bell_diagonal",
        node_template=template,
    )
    user_names = {name_of(u) for u in users}
    for node in config["nodes"]:
        if node.get("type") == "QuantumRouter":
            node["memo_size"] = USER_MEM if node["name"] in user_names else Q_R
    return config


def rsvp_tree(graph, users, switches, tree, physics: bool) -> dict:
    configure_kernel()
    want_n = max(0, len(users) - 1)
    tree_paths = [[name_of(n) for n in ch.path] for ch in tree]
    planner_paths = [list(ch.path) for ch in tree]
    planner_p = tree_rate(graph, planner_paths, Q_SWAP, ALPHA, complete=len(tree) == want_n)

    config = make_waxman_config(graph, users, switches, 1.25 if physics else 0.15)
    metrics.configure("in_memory")
    t0 = time.perf_counter()
    topo = sq.RouterNetTopo(config)
    tl = topo.get_timeline()
    tl.show_progress = False
    routers = {n.name: n for n in topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)}
    for router in routers.values():
        router.network_manager.set_forwarding_table({})
        router.swapping_success_prob = Q_SWAP
    for path in tree_paths:
        pin_path(routers, path)
    for u in users:
        sq.RequestApp(routers[name_of(u)])
    starts = assign_starts(tree_paths)
    tl.init()
    for s in starts:
        routers[s["initiator"]].app.start(s["responder"], 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    tl.run()
    wall = time.perf_counter() - t0

    accepted = []
    seen = set()
    for router in routers.values():
        for res in router.network_manager.rsvp.accepted_reservations:
            key = (res.initiator, res.responder)
            if key in seen:
                continue
            seen.add(key)
            accepted.append({"initiator": res.initiator, "responder": res.responder, "path": list(res.path)})

    want = {frozenset((s["initiator"], s["responder"])): s["path"] for s in starts}
    match = []
    admitted_int_paths = []
    for res in accepted:
        key = frozenset((res["initiator"], res["responder"]))
        pinned = want.get(key, [])
        got = res["path"]
        match.append(got == pinned or got == list(reversed(pinned)))
        admitted_int_paths.append([int_of(x) for x in got])

    complete = len(accepted) == want_n and want_n > 0
    eq2 = tree_rate(graph, admitted_int_paths, Q_SWAP, ALPHA, complete=complete)
    switch_names = [name_of(s) for s in switches]
    return {
        "n_planner_channels": len(tree),
        "n_admitted": len(accepted),
        "want_n": want_n,
        "complete_tree": complete,
        "rsvp_paths_match_pin": all(match) and len(accepted) == len(starts) and len(starts) > 0,
        "planner_eq2": planner_p,
        "admitted_eq2": eq2,
        "occupancy": occupancy(routers, switch_names),
        "wall_s": wall,
        "physics": physics,
        "counters": {name_of(u): int(routers[name_of(u)].app.memory_counter) for u in users if routers[name_of(u)].app},
    }


def algs_on_waxman() -> dict:
    graph, users, switches = make_instance("waxman", 10, 50, 6.0, 10_000.0, seed=0)
    sw = set(switches)
    out = {
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "n_users": len(users),
        "n_switches": len(switches),
        "solvers": {},
    }
    for name in ("alg2", "alg3", "alg4"):
        solver = SOLVERS[name]
        tree, rate = solver(graph, users, sw, Q_R, ALPHA, Q_SWAP)
        kernel = rsvp_tree(graph, users, switches, tree, physics=False)
        out["solvers"][name] = {
            "planner_product": rate,
            "kernel": kernel,
        }
    return out


def two_groups(q_r: int = Q_R) -> dict:
    graph, users, switches = make_instance("waxman", 10, 50, 6.0, 10_000.0, seed=0)
    g0, g1 = users[:5], users[5:]
    sw = set(switches)
    tree0, p0 = algorithm4(graph, g0, sw, q_r, ALPHA, Q_SWAP)
    # Same Q_r pool: pin both trees on one topo, start group 0 then group 1.
    configure_kernel()
    config = make_waxman_config(graph, users, switches, 0.15)
    for node in config["nodes"]:
        if node.get("type") == "QuantumRouter" and node["name"] not in {name_of(u) for u in users}:
            node["memo_size"] = q_r
    metrics.configure("in_memory")
    topo = sq.RouterNetTopo(config)
    tl = topo.get_timeline()
    tl.show_progress = False
    routers = {n.name: n for n in topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)}
    for router in routers.values():
        router.network_manager.set_forwarding_table({})
        router.swapping_success_prob = Q_SWAP
    for tree in (tree0,):
        for ch in tree:
            pin_path(routers, [name_of(n) for n in ch.path])
    tree1, p1 = algorithm4(graph, g1, sw, q_r, ALPHA, Q_SWAP)
    for ch in tree1:
        pin_path(routers, [name_of(n) for n in ch.path])
    for u in users:
        sq.RequestApp(routers[name_of(u)])
    starts0 = assign_starts([[name_of(n) for n in ch.path] for ch in tree0])
    starts1 = assign_starts([[name_of(n) for n in ch.path] for ch in tree1])
    tl.init()
    for s in starts0:
        routers[s["initiator"]].app.start(s["responder"], 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    for s in starts1:
        routers[s["initiator"]].app.start(s["responder"], 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    tl.run()

    def admitted_for(starts):
        keys = {frozenset((s["initiator"], s["responder"])) for s in starts}
        got = []
        for router in routers.values():
            for res in router.network_manager.rsvp.accepted_reservations:
                if frozenset((res.initiator, res.responder)) in keys:
                    got.append(list(res.path))
        # unique
        uniq = []
        seen = set()
        for path in got:
            key = frozenset((path[0], path[-1]))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(path)
        return uniq

    a0 = admitted_for(starts0)
    a1 = admitted_for(starts1)
    int0 = [[int_of(x) for x in p] for p in a0]
    int1 = [[int_of(x) for x in p] for p in a1]
    occ = occupancy(routers, [name_of(s) for s in switches], q_r)
    return {
        "group0": {
            "users": g0,
            "planner_n": len(tree0),
            "planner_eq2": p0,
            "n_admitted": len(a0),
            "eq2": tree_rate(graph, int0, Q_SWAP, ALPHA, complete=len(a0) == 4),
        },
        "group1": {
            "users": g1,
            "planner_n": len(tree1),
            "planner_eq2": p1,
            "n_admitted": len(a1),
            "eq2": tree_rate(graph, int1, Q_SWAP, ALPHA, complete=len(a1) == 4),
        },
        "shared_occupancy": occ,
        "q_r": q_r,
        "note": "Two 5-user trees, one Q_r pool. Eq. (2) is 0 if a group is incomplete.",
    }


def star_fidelity_and_slot() -> dict:
    """Fig. 4a star: Eq. (2) from admission, then EG with fidelity events."""
    configure_kernel()
    graph = build_star(3, length=10.0, attenuation=0.0002)
    att = -10.0 * math.log10(P_STAR) / 5000.0
    template = {
        "router_template": {
            "MemoryArray": {
                "frequency": 1e6,
                "coherence_time": 0.05,
                "efficiency": 1,
                "fidelity": 0.9,
                "cutoff_flag": True,
            },
            "EntanglementSwapping": {"swapping_success_prob": Q_SWAP},
        },
        "bsm_template": default_template["bsm_template"],
    }
    config, _ = generate_config(
        graph,
        cc_delay=1,
        memory_size=8,
        output_file="",
        output_directory="",
        stop_time=1.25,
        formalism="bell_diagonal",
        node_template=template,
    )
    for qc in config.get("qchannels", []):
        qc["attenuation"] = att
    for node in config["nodes"]:
        if node.get("type") == "QuantumRouter":
            node["memo_size"] = 8 if node["name"] != "router_0" else 4

    metrics.configure("in_memory")
    metrics.enable([EG_METRIC, ES_METRIC, SWAPPED_FIDELITIES_METRIC, THROUGHPUT_METRIC])
    topo = sq.RouterNetTopo(config)
    tl = topo.get_timeline()
    tl.show_progress = False
    routers = {n.name: n for n in topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)}
    for name in ("router_1", "router_2", "router_3"):
        sq.RequestApp(routers[name])
    routers["router_0"].swapping_success_prob = Q_SWAP
    tl.init()
    routers["router_1"].app.start("router_2", 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    routers["router_3"].app.start("router_1", 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    tl.run()

    es = metrics.storage.get_by_event(EventTypes.ES_SUCCESS)
    eg = metrics.storage.get_by_event(EventTypes.EG_SUCCESS)
    deliv = metrics.storage.get_by_event(EventTypes.DELIVERY)
    es_fids = [float(r.data.fidelity) for r in es if getattr(r.data, "fidelity", None) is not None]
    del_fids = [float(r.data.fidelity) for r in deliv if getattr(r.data, "fidelity", None) is not None]
    eg_fids = [float(r.data.fidelity) for r in eg if getattr(r.data, "fidelity", None) is not None]
    admitted = []
    for router in routers.values():
        for res in router.network_manager.rsvp.accepted_reservations:
            admitted.append(list(res.path))
    # Eq. (2) for this star uses p=0.9, two length-2 channels if both admitted.
    n_ok = len({frozenset((p[0], p[-1])) for p in admitted})
    slot_p = (P_STAR ** 2 * Q_SWAP) ** 2 if n_ok >= 2 else 0.0
    return {
        "native_eq2": False,
        "eq2_from_admission": slot_p,
        "n_admitted_channels": n_ok,
        "n_eg_success": len(eg),
        "n_es_success": len(es),
        "n_delivery": len(deliv),
        "eg_fidelity_n": len(eg_fids),
        "eg_fidelity_mean": sum(eg_fids) / len(eg_fids) if eg_fids else None,
        "es_fidelity_n": len(es_fids),
        "es_fidelity_mean": sum(es_fids) / len(es_fids) if es_fids else None,
        "es_fidelity_min": min(es_fids) if es_fids else None,
        "delivery_fidelity_n": len(del_fids),
        "delivery_fidelity_mean": sum(del_fids) / len(del_fids) if del_fids else None,
        "delivery_fidelity_min": min(del_fids) if del_fids else None,
        "coherence_s": 0.05,
        "note": "Fidelity from SeQUeNCe event payloads, not a per-channel trajectory object.",
    }


def main() -> int:
    OUT.mkdir(exist_ok=True)
    payload = {
        "eq2": {
            "native_in_sequence": False,
            "adapter": "muerp.eq2.tree_rate",
            "rule": "P=0 if the admitted set is not a complete spanning tree",
        },
        "slot_model": {
            "simultaneous_attempts_in_kernel": False,
            "what_we_use": "RSVP then Eq. (2). That is Zeng et al.'s slot, computed outside SeQUeNCe.",
        },
        "volchenkov": {
            "exact_physica_a_2002": False,
            "still": "Barabási–Albert stand-in in graphs.py",
        },
        "replicas_20": "run separately: N_REPLICAS in run_sweeps.py",
        "algs_on_waxman_10_50": algs_on_waxman(),
        "two_groups_sharing_Qr": two_groups(Q_R),
        "two_groups_Qr2": two_groups(2),
        "star_fidelity_and_eq2": star_fidelity_and_slot(),
    }
    path = OUT / "showcase_kernel.json"
    path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
