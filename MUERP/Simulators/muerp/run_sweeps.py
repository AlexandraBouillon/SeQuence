"""Paper-style Figs. 5–8 on the analytic MUERP model (SeQUeNCe-side planner)."""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from .algorithms import SOLVERS
from .graphs import make_instance

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ALPHA = 1e-4
AREA = 10_000.0
DEFAULT_U, DEFAULT_R, DEFAULT_D, DEFAULT_Q, DEFAULT_QSWAP = 10, 50, 6.0, 4, 0.9
N_REPLICAS = 20
ALG_NAMES = ["alg2", "alg3", "alg4", "e_qcast", "n_fusion"]


def evaluate(kind, n_u, n_r, degree, q_cap, q_swap, seed) -> dict[str, float]:
    graph, users, switches = make_instance(kind, n_u, n_r, degree, AREA, seed)
    sw = set(switches)
    out = {}
    for name in ALG_NAMES:
        solver = SOLVERS[name]
        _tree, rate = solver(graph, users, sw, q_cap, ALPHA, q_swap)
        out[name] = rate
    return out


def mean_std(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    summary = {}
    for name in ALG_NAMES:
        vals = np.array([row[name] for row in rows], dtype=float)
        summary[name] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "p_zero": float(np.mean(vals == 0.0)),
        }
    return summary


def run_fig5() -> dict:
    result = {}
    for kind in ("waxman", "watts_strogatz", "volchenkov"):
        rows = [
            evaluate(kind, DEFAULT_U, DEFAULT_R, DEFAULT_D, DEFAULT_Q, DEFAULT_QSWAP, seed)
            for seed in range(N_REPLICAS)
        ]
        result[kind] = mean_std(rows)
    return result


def run_fig6a() -> dict:
    result = {}
    for n_u in (4, 6, 8, 10, 12):
        rows = [
            evaluate("waxman", n_u, DEFAULT_R, DEFAULT_D, DEFAULT_Q, DEFAULT_QSWAP, seed)
            for seed in range(N_REPLICAS)
        ]
        result[str(n_u)] = mean_std(rows)
    return result


def run_fig6b() -> dict:
    result = {}
    for n_r in (20, 30, 40, 50, 60):
        rows = [
            evaluate("waxman", DEFAULT_U, n_r, DEFAULT_D, DEFAULT_Q, DEFAULT_QSWAP, seed)
            for seed in range(N_REPLICAS)
        ]
        result[str(n_r)] = mean_std(rows)
    return result


def run_fig7a() -> dict:
    result = {}
    for degree in (2, 4, 6, 8, 10):
        rows = [
            evaluate("waxman", DEFAULT_U, DEFAULT_R, float(degree), DEFAULT_Q, DEFAULT_QSWAP, seed)
            for seed in range(N_REPLICAS)
        ]
        result[str(degree)] = mean_std(rows)
    return result


def run_fig7b() -> dict:
    """Start from 600 edges; drop 30 per step (paper Fig. 7b)."""
    from .graphs import build_waxman, split_users_switches

    n = DEFAULT_U + DEFAULT_R
    result = defaultdict(list)
    for seed in range(N_REPLICAS):
        rng = np.random.default_rng(1000 + seed)
        graph = build_waxman(n, AREA, 600, rng)
        users, switches = split_users_switches(DEFAULT_U, DEFAULT_R)
        sw = set(switches)
        removed = 0
        while graph.number_of_edges() >= n and removed <= 450:
            rates = {}
            for name in ALG_NAMES:
                solver = SOLVERS[name]
                _tree, rate = solver(graph, users, sw, DEFAULT_Q, ALPHA, DEFAULT_QSWAP)
                rates[name] = rate
            result[removed].append(rates)
            if all(v == 0.0 for v in rates.values()):
                break
            edges = list(graph.edges)
            rng.shuffle(edges)
            dropped = 0
            for u, v in edges:
                graph.remove_edge(u, v)
                dropped += 1
                if dropped >= 30:
                    break
            removed += dropped
    out = {}
    for k, rows in result.items():
        out[str(k)] = mean_std(rows)
    return out


def run_fig8a() -> dict:
    result = {}
    for q_cap in (2, 4, 6, 8):
        rows = [
            evaluate("waxman", DEFAULT_U, DEFAULT_R, DEFAULT_D, q_cap, DEFAULT_QSWAP, seed)
            for seed in range(N_REPLICAS)
        ]
        result[str(q_cap)] = mean_std(rows)
    return result


def run_fig8b() -> dict:
    result = {}
    for q_swap in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        rows = [
            evaluate("waxman", DEFAULT_U, DEFAULT_R, DEFAULT_D, DEFAULT_Q, q_swap, seed)
            for seed in range(N_REPLICAS)
        ]
        result[str(q_swap)] = mean_std(rows)
    return result


def main() -> int:
    OUT.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    payload = {
        "replicas": N_REPLICAS,
        "note": "Analytic Eq. (1)–(2). 10 replicas (paper uses 20). Volchenkov = BA stand-in.",
        "fig5_topology": run_fig5(),
        "fig6a_users": run_fig6a(),
        "fig6b_switches": run_fig6b(),
        "fig7a_degree": run_fig7a(),
        "fig7b_removed_edges": run_fig7b(),
        "fig8a_qubits": run_fig8a(),
        "fig8b_qswap": run_fig8b(),
        "seconds": 0.0,
    }
    payload["seconds"] = time.perf_counter() - t0
    path = OUT / "figs_5_8.json"
    path.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"seconds": payload["seconds"], "wrote": str(path)}, indent=2))
    print("fig5", {k: {a: v[a]["mean"] for a in ALG_NAMES} for k, v in payload["fig5_topology"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
