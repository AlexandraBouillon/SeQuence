"""PDF figures for the LaTeX writeup."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ALG_STYLE = {
    "alg2": ("Alg. 2", "o-"),
    "alg3": ("Alg. 3", "s-"),
    "alg4": ("Alg. 4", "^-"),
    "e_qcast": ("E-Q-CAST", "x--"),
    "n_fusion": ("N-FUSION", "d--"),
}


def _plot_group(data: dict, xlabel: str, outfile: Path, xtype=float) -> None:
    xs = sorted(data.keys(), key=lambda k: xtype(k))
    plt.figure(figsize=(5.2, 3.4))
    for key, (label, fmt) in ALG_STYLE.items():
        ys = [data[x][key]["mean"] for x in xs]
        plt.plot([xtype(x) for x in xs], ys, fmt, label=label, linewidth=1.2, markersize=5)
    plt.xlabel(xlabel)
    plt.ylabel(r"Entanglement rate $P$")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(outfile)
    plt.close()


def main() -> None:
    payload = json.loads((OUT / "figs_5_8.json").read_text())
    OUT.mkdir(exist_ok=True)

    # Fig 5: bar chart by topology
    plt.figure(figsize=(5.2, 3.4))
    topos = ["waxman", "watts_strogatz", "volchenkov"]
    x = range(len(topos))
    width = 0.15
    for i, key in enumerate(ALG_STYLE):
        means = [payload["fig5_topology"][t][key]["mean"] for t in topos]
        xs = [xi + (i - 2) * width for xi in x]
        plt.bar(xs, means, width, label=ALG_STYLE[key][0])
    plt.xticks(list(x), ["Waxman", "Watts–Strogatz", "Volchenkov*"])
    plt.ylabel(r"Entanglement rate $P$")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / "fig5_topology.pdf")
    plt.close()

    _plot_group(payload["fig6a_users"], r"Number of users $|U|$", OUT / "fig6a_users.pdf", int)
    _plot_group(payload["fig6b_switches"], r"Number of switches $|R|$", OUT / "fig6b_switches.pdf", int)
    _plot_group(payload["fig7a_degree"], r"Average degree $D$", OUT / "fig7a_degree.pdf", int)
    _plot_group(payload["fig7b_removed_edges"], r"Removed optical fibers", OUT / "fig7b_removed.pdf", int)
    _plot_group(payload["fig8a_qubits"], r"Switch qubits $Q_r$", OUT / "fig8a_qubits.pdf", int)
    _plot_group(payload["fig8b_qswap"], r"Swap success $q$", OUT / "fig8b_qswap.pdf", float)
    print("wrote PDFs in", OUT)


if __name__ == "__main__":
    main()
