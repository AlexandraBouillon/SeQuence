"""Wall-clock of a linear repeater chain in SeQUeNCe 1.3.1.

Not the MUERP score (M14). MUERP is a tree on a random graph, not a chain.
This is the 'long repeater chain' datapoint the findings file refused to use as a grade.
"""

from __future__ import annotations

import json
import resource
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "muerp" / "results"
CHAIN_SIZES = (2, 5, 10, 20, 50)
Q_SWAP = 0.9
MEMO = 8
WINDOW_S = 0.2


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)


def run_chain(n_routers: int, physics: bool) -> dict:
    import sequence as sq
    from sequence.constants import SECOND, SINGLE_HERALDED
    from sequence.utils.graphs import build_linear
    from sequence.utils.nx_converter import default_template, generate_config, router_name_func

    sq.EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    sq.EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
    sq.EntanglementSwappingA.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)
    sq.EntanglementSwappingB.set_formalism(sq.constants.BELL_DIAGONAL_STATE_FORMALISM)

    src, dst = router_name_func(0), router_name_func(n_routers - 1)
    hops = n_routers - 1
    stop = 1.2 if physics else 0.1
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

    t_gen0 = time.perf_counter()
    graph = build_linear(n_routers, length=10.0, attenuation=0.0002)
    config, _ = generate_config(
        graph,
        cc_delay=1,
        memory_size=MEMO,
        output_file="",
        output_directory="",
        stop_time=stop,
        formalism="bell_diagonal",
        node_template=template,
    )
    t_gen = time.perf_counter() - t_gen0

    t_topo0 = time.perf_counter()
    topo = sq.RouterNetTopo(config)
    tl = topo.get_timeline()
    tl.show_progress = False
    routers = {n.name: n for n in topo.get_nodes_by_type(sq.RouterNetTopo.QUANTUM_ROUTER)}
    sq.RequestApp(routers[src])
    t_topo = time.perf_counter() - t_topo0

    t_run0 = time.perf_counter()
    tl.init()
    routers[src].app.start(dst, 1 * SECOND, 1.2 * SECOND, 1, 0.5)
    tl.run()
    t_run = time.perf_counter() - t_run0

    accepted = []
    for router in routers.values():
        for res in router.network_manager.rsvp.accepted_reservations:
            accepted.append({"initiator": res.initiator, "responder": res.responder, "path_len": len(res.path)})
    admitted = any(a["initiator"] == src and a["responder"] == dst for a in accepted)
    path_len = next((a["path_len"] for a in accepted if a["initiator"] == src), 0)
    counter = int(routers[src].app.memory_counter) if routers[src].app else 0
    return {
        "n_routers": n_routers,
        "hops": hops,
        "physics": physics,
        "admitted": admitted,
        "rsvp_path_len": path_len,
        "memory_counter": counter,
        "gen_s": t_gen,
        "topo_s": t_topo,
        "run_s": t_run,
        "wall_s": t_gen + t_topo + t_run,
        "peak_rss_mb": rss_mb(),
        "window_s": WINDOW_S if physics else 0.0,
        "q": Q_SWAP,
        "memo_size": MEMO,
        "src": src,
        "dst": dst,
    }


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        n = int(sys.argv[2])
        physics = sys.argv[3] == "physics"
        print(json.dumps(run_chain(n, physics)))
        return 0

    OUT.mkdir(exist_ok=True)
    py = sys.executable
    rows = []
    for n in CHAIN_SIZES:
        for mode in ("admit", "physics"):
            t0 = time.perf_counter()
            proc = subprocess.run(
                [py, str(Path(__file__).resolve()), "--worker", str(n), mode],
                capture_output=True,
                text=True,
                check=False,
            )
            spawn_s = time.perf_counter() - t0
            if proc.returncode != 0:
                rows.append(
                    {
                        "n_routers": n,
                        "physics": mode == "physics",
                        "error": proc.stderr[-2000:],
                        "spawn_s": spawn_s,
                    }
                )
                print(f"FAIL n={n} {mode}: {proc.stderr[-400:]}", file=sys.stderr)
                continue
            row = json.loads(proc.stdout.strip().splitlines()[-1])
            row["spawn_s"] = spawn_s
            rows.append(row)
            print(
                f"n={n:3d} {mode:7s} wall={row['wall_s']:.3f}s "
                f"topo={row['topo_s']:.3f}s run={row['run_s']:.3f}s "
                f"rss={row['peak_rss_mb']:.0f}MB admitted={row['admitted']} "
                f"pairs={row['memory_counter']}"
            )

    payload = {
        "note": "Linear SeQUeNCe chain. Not MUERP M14. Not NetSquid.",
        "sizes": list(CHAIN_SIZES),
        "rows": rows,
    }
    path = OUT / "repeater_chain_speed.json"
    path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
