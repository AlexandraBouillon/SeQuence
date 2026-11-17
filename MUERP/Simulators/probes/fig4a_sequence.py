"""Fig. 4a probe on SeQUeNCe 1.3.1 (admission + analytic P).

Paper instance: 3 users + 1 switch, two channels Alice-Bob and Alice-Carol.
Case A: Q_S = 4 -> both channels reserved, P = (p^2 q)^2.
Case B: Q_S = 2 -> infeasible, P = 0.

Does not run Algorithms 1-4. Does not use Monte Carlo throughput as Eq. (2).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import sequence as sq
from sequence.constants import SECOND, SINGLE_HERALDED
from sequence.utils import metrics
from sequence.utils.graphs import build_star
from sequence.utils.metrics.builtins import ADMISSION_RATE_METRIC, MEMORY_UTILIZATION_RATIO_METRIC
from sequence.utils.nx_converter import generate_config

HERE = Path(__file__).resolve().parent
SWITCH = "router_0"
ALICE = "router_1"
BOB = "router_2"
CAROL = "router_3"
USERS = (ALICE, BOB, CAROL)
CHANNELS = ((ALICE, BOB), (ALICE, CAROL))
P_LINK = 0.9
Q_SWAP = 0.9
USER_MEMORIES = 8


def analytic_tree_rate(admitted: list[bool], p: float, q: float) -> float:
    """Eq. (2) for two length-2 channels: each P_A = p^2 q. Infeasible -> 0."""
    if not all(admitted):
        return 0.0
    p_channel = (p ** 2) * q
    return p_channel ** 2


def make_config(q_s: int, q: float = Q_SWAP) -> dict:
    graph = build_star(3, length=10.0, attenuation=0.0002)
    config, _names = generate_config(
        graph,
        cc_delay=1,
        memory_size=USER_MEMORIES,
        output_file="",
        output_directory="",
        stop_time=0.1,
        formalism="bell_diagonal",
    )
    config["templates"]["router_template"]["EntanglementSwapping"] = {
        "swapping_success_prob": q,
    }
    for node in config["nodes"]:
        if node.get("type") != "QuantumRouter":
            continue
        if node["name"] == SWITCH:
            node["memo_size"] = q_s
        else:
            node["memo_size"] = USER_MEMORIES
    return config


def switch_reserved_memories(network_topo: sq.RouterNetTopo) -> int:
    switch = next(
        node
        for node in network_topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)
        if node.name == SWITCH
    )
    occupied = 0
    for card in switch.network_manager.get_timecards():
        if card.reservations:
            occupied += 1
    return occupied


def run_case(q_s: int, p: float = P_LINK, q: float = Q_SWAP) -> dict:
    sq.EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(SINGLE_HERALDED)

    config = make_config(q_s, q)
    json_path = HERE / f"fig4a_qs{q_s}.json"
    json_path.write_text(json.dumps(config, indent=2))

    metrics.configure("in_memory")
    network_topo = sq.RouterNetTopo(config)
    timeline = network_topo.get_timeline()
    timeline.show_progress = False
    metrics.enable([ADMISSION_RATE_METRIC, MEMORY_UTILIZATION_RATIO_METRIC])

    routers = {
        node.name: node
        for node in network_topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)
    }
    for name in USERS:
        sq.RequestApp(routers[name])

    switch = routers[SWITCH]
    switch.swapping_success_prob = q

    timeline.init()
    apps = {name: routers[name].app for name in USERS}
    for responder in (BOB, CAROL):
        apps[ALICE].start(
            responder=responder,
            start_t=1 * SECOND,
            end_t=2 * SECOND,
            memo_size=1,
            fidelity=0.5,
        )
    timeline.run()

    # Alice.RequestApp.path is overwritten by the second start(); read RSVP instead.
    accepted = list(switch.network_manager.rsvp.accepted_reservations)
    admitted_by_responder = {res.responder: True for res in accepted}
    admitted = [bool(admitted_by_responder.get(dst, False)) for _, dst in CHANNELS]
    paths = {res.responder: list(res.path) for res in accepted}

    rate = analytic_tree_rate(admitted, p, q)
    return {
        "q_s": q_s,
        "p": p,
        "q": q,
        "config": str(json_path),
        "admitted": {f"{ALICE}-{dst}": ok for (_, dst), ok in zip(CHANNELS, admitted)},
        "paths": {f"{ALICE}-{dst}": paths.get(dst, []) for _, dst in CHANNELS},
        "switch_memories_reserved": switch_reserved_memories(network_topo),
        "switch_memo_size": switch.components[switch.memo_arr_name].__len__(),
        "alice_reservation_result_last_only": apps[ALICE].reservation_result,
        "P": rate,
        "expected_P": (p ** 2 * q) ** 2 if q_s >= 4 else 0.0,
    }


def main() -> int:
    results = [run_case(4), run_case(2)]
    out_path = HERE / "fig4a_sequence_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

    case_a, case_b = results
    a_ok = all(case_a["admitted"].values()) and case_a["P"] == case_a["expected_P"]
    b_ok = (not all(case_b["admitted"].values())) and case_b["P"] == 0.0
    print(f"Case A (Qs=4) match: {a_ok}")
    print(f"Case B (Qs=2) match: {b_ok}")
    print(f"Wrote {out_path}")
    return 0 if a_ok and b_ok else 1


if __name__ == "__main__":
    sys.exit(main())
