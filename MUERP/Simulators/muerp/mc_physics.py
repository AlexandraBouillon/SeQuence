"""Monte Carlo of Eq. (1)–(2) and a short SeQUeNCe Fig. 4a physics run."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
P_LINK = 0.9
Q_SWAP = 0.9
N_TRIALS = 20_000


def slot_mc(p: float, q: float, n: int, rng: np.random.Generator) -> dict:
    """Fig. 4a: two channels, each two links + one swap. Tree P = (p^2 q)^2."""
    analytic = (p ** 2 * q) ** 2
    # one slot: 4 links, 2 swaps, all independent; tree ok iff all succeed
    links = rng.random((n, 4)) < p
    swaps = rng.random((n, 2)) < q
    ch0 = links[:, 0] & links[:, 1] & swaps[:, 0]
    ch1 = links[:, 2] & links[:, 3] & swaps[:, 1]
    tree = ch0 & ch1
    return {
        "analytic_P": analytic,
        "mc_mean": float(tree.mean()),
        "mc_std": float(tree.std() / math.sqrt(n)),
        "n_trials": n,
    }


def sequence_fig4a_physics(p: float, q: float) -> dict:
    """Run SeQUeNCe EG for Case A; throughput is not Eq. (2)."""
    import sequence as sq
    from sequence.constants import SECOND, SINGLE_HERALDED
    from sequence.utils.graphs import build_star
    from sequence.utils.nx_converter import generate_config

    sq.EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    sq.EntanglementSwappingA.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)
    sq.EntanglementSwappingB.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)
    graph = build_star(3, length=10.0, attenuation=0.0002)
    # Homogeneous link transmittance ~ p on each 5 km half-link (dB/m).
    # p = 10^(-att * 5000 / 10) => att = -10 log10(p) / 5000
    att = -10.0 * math.log10(p) / 5000.0
    config, _ = generate_config(
        graph,
        cc_delay=1,
        memory_size=8,
        output_file="",
        output_directory="",
        stop_time=1.25,
        formalism="bell_diagonal",
        node_template=None,
    )
    for qc in config.get("qchannels", []):
        qc["attenuation"] = att
    config["templates"]["router_template"]["EntanglementSwapping"] = {
        "swapping_success_prob": q,
    }
    for node in config["nodes"]:
        if node.get("type") == "QuantumRouter":
            node["memo_size"] = 8 if node["name"] != "router_0" else 4

    t0 = time.perf_counter()
    topo = sq.RouterNetTopo(config)
    tl = topo.get_timeline()
    tl.show_progress = False
    routers = {n.name: n for n in topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)}
    for name in ("router_1", "router_2", "router_3"):
        sq.RequestApp(routers[name])
    routers["router_0"].swapping_success_prob = q
    tl.init()
    # One RequestApp per router: Alice–Bob and Carol–Alice (same two channels).
    routers["router_1"].app.start("router_2", 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    routers["router_3"].app.start("router_1", 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    tl.run()
    elapsed = time.perf_counter() - t0
    return {
        "alice_bob_counter": int(routers["router_1"].app.memory_counter),
        "carol_alice_counter": int(routers["router_3"].app.memory_counter),
        "window_s": 0.2,
        "wall_s": elapsed,
        "note": "SeQUeNCe retries over a time window; counters are throughput, not slot P.",
    }


def main() -> int:
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(0)
    payload = {"slot_mc": slot_mc(P_LINK, Q_SWAP, N_TRIALS, rng)}
    try:
        payload["sequence_physics"] = sequence_fig4a_physics(P_LINK, Q_SWAP)
    except Exception as exc:  # noqa: BLE001
        payload["sequence_physics"] = {"error": str(exc)}
    path = OUT / "mc_physics.json"
    path.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
