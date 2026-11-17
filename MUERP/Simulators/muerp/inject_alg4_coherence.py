"""Inject Alg. 4's Fig. 4a tree into SeQUeNCe RSVP, then run EG with coherence off vs on."""

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
    MEMORY_DECOHERENCE_RATE_METRIC,
    THROUGHPUT_METRIC,
)
from sequence.utils.metrics.event_types import EventTypes
from sequence.utils.nx_converter import default_template, generate_config, router_name_func

from .algorithms import algorithm4

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
P_LINK = 0.9
Q_SWAP = 0.9
ALPHA = 1e-4
SWITCH_ID = 0
USER_IDS = [1, 2, 3]


def name_of(node: int) -> str:
    return router_name_func(node)


def pin_path(routers: dict, path: list[str]) -> None:
    """Install next-hop rules for path and its reverse (RSVP needs both)."""
    for seq in (path, list(reversed(path))):
        dest = seq[-1]
        for node, nxt in zip(seq[:-1], seq[1:]):
            routers[node].network_manager.get_routing_protocol().update_forwarding_rule(dest, nxt)


def make_config(q_s: int, coherence_s: float, cutoff: bool) -> dict:
    graph = build_star(3, length=10.0, attenuation=0.0002)
    att = -10.0 * math.log10(P_LINK) / 5000.0
    template = {
        "router_template": {
            "MemoryArray": {
                "frequency": 200000000.0,
                "coherence_time": coherence_s,
                "efficiency": 1,
                "fidelity": 0.9,
                "cutoff_flag": cutoff,
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
        stop_time=1.3,
        formalism="bell_diagonal",
        node_template=template,
    )
    for qc in config.get("qchannels", []):
        qc["attenuation"] = att
    for node in config["nodes"]:
        if node.get("type") == "QuantumRouter":
            node["memo_size"] = 8 if node["name"] != name_of(SWITCH_ID) else q_s
    return config


def configure_kernel() -> None:
    sq.EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    sq.EntanglementSwappingA.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)
    sq.EntanglementSwappingB.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)


def run_injected(
    q_s: int,
    coherence_s: float,
    cutoff: bool,
    physics: bool,
) -> dict:
    configure_kernel()
    graph = build_star(3, length=10.0)
    tree, analytic_p = algorithm4(graph, USER_IDS, {SWITCH_ID}, q_s, ALPHA, Q_SWAP)
    tree_paths = [[name_of(n) for n in ch.path] for ch in tree]

    config = make_config(q_s, coherence_s, cutoff)
    if not physics:
        config["stop_time"] = int(0.1 * SECOND)

    metrics.configure("in_memory")
    topo = sq.RouterNetTopo(config)
    tl = topo.get_timeline()
    tl.show_progress = False
    metrics.enable([EG_METRIC, ES_METRIC, THROUGHPUT_METRIC, MEMORY_DECOHERENCE_RATE_METRIC])

    routers = {n.name: n for n in topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)}
    for router in routers.values():
        router.network_manager.set_forwarding_table({})
        router.swapping_success_prob = Q_SWAP
    for path in tree_paths:
        pin_path(routers, path)

    users = [name_of(u) for u in USER_IDS]
    for uname in users:
        sq.RequestApp(routers[uname])

    tl.init()
    used_initiators: set[str] = set()
    starts = []
    for ch, path in zip(tree, tree_paths):
        src, dst = path[0], path[-1]
        if src in used_initiators:
            src, dst = dst, src
            path = list(reversed(path))
        used_initiators.add(src)
        routers[src].app.start(dst, 1 * SECOND, 1.2 * SECOND, 1, 0.5)
        starts.append({"initiator": src, "responder": dst, "pinned_path": path})

    t0 = time.perf_counter()
    tl.run()
    wall = time.perf_counter() - t0

    accepted = []
    for router in routers.values():
        for res in router.network_manager.rsvp.accepted_reservations:
            key = (res.initiator, res.responder)
            if key not in {(a["initiator"], a["responder"]) for a in accepted}:
                accepted.append(
                    {
                        "initiator": res.initiator,
                        "responder": res.responder,
                        "rsvp_path": list(res.path),
                    }
                )

    pinned = {frozenset((s["initiator"], s["responder"])): s["pinned_path"] for s in starts}
    path_match = []
    for res in accepted:
        key = frozenset((res["initiator"], res["responder"]))
        want = pinned.get(key, [])
        got = res["rsvp_path"]
        path_match.append(got == want or got == list(reversed(want)))

    deliveries = len(metrics.storage.get_by_event(EventTypes.DELIVERY))
    expired = len(metrics.storage.get_by_event(EventTypes.MEMORY_EXPIRED))
    eg_ok = len(metrics.storage.get_by_event(EventTypes.EG_SUCCESS))
    es_ok = len(metrics.storage.get_by_event(EventTypes.ES_SUCCESS))
    counters = {
        name: int(routers[name].app.memory_counter) if routers[name].app else 0 for name in users
    }
    return {
        "q_s": q_s,
        "coherence_s": coherence_s,
        "cutoff": cutoff,
        "physics": physics,
        "alg4_channels": [
            {"src": name_of(ch.src), "dst": name_of(ch.dst), "path": [name_of(n) for n in ch.path], "rate": ch.rate}
            for ch in tree
        ],
        "alg4_P": analytic_p,
        "starts": starts,
        "accepted": accepted,
        "n_tree": len(tree),
        "n_admitted": len(accepted),
        "rsvp_paths_match_alg4": all(path_match) and len(accepted) == len(tree) and len(tree) > 0,
        "path_match_detail": path_match,
        "deliveries": deliveries,
        "memory_expired": expired,
        "eg_success": eg_ok,
        "es_success": es_ok,
        "app_counters": counters,
        "wall_s": wall,
        "complete_tree": len(tree) == 2,
    }


def main() -> int:
    OUT.mkdir(exist_ok=True)
    payload = {
        "admit_qs4": run_injected(4, coherence_s=-1, cutoff=False, physics=False),
        "admit_qs2": run_injected(2, coherence_s=-1, cutoff=False, physics=False),
        "physics_coh_off": run_injected(4, coherence_s=-1, cutoff=False, physics=True),
        "physics_coh_on": run_injected(4, coherence_s=0.01, cutoff=True, physics=True),
    }
    path = OUT / "inject_alg4_coherence.json"
    path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    print(f"Wrote {path}")
    a4 = payload["admit_qs4"]["rsvp_paths_match_alg4"]
    a2 = payload["admit_qs2"]["n_admitted"] < 2
    coh = payload["physics_coh_on"]["memory_expired"] >= payload["physics_coh_off"]["memory_expired"]
    print(f"M5 path pin Qs=4: {a4}")
    print(f"M2/M5 Qs=2 incomplete tree: {a2} (admitted {payload['admit_qs2']['n_admitted']})")
    print(f"M11 expired on >= off: {coh}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
