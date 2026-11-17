# Simulator rating metrics for MUERP (Zeng et al., ICDCS 2024)

Rate **NetSquid** and **SeQUeNCe** against this paper, not as general quantum-network tools. Architecture notes live in `_v0.tex`. These metrics decide whether a simulator can **reproduce** the multi-user entanglement routing problem (MUERP) and support the **extensions the paper names**.

**Paper source:** `../MultiUser_Paper_1.md` (Zeng et al., ICDCS 2024).

---

## What this paper actually needs

The ICDCS evaluation is a **graph routing experiment**, not a device-physics bake-off.

- Topology \(G = (V,E)\), \(V = U \cup R\): users vs switches, optical-fiber edges (Sec. II-A).
- Each switch has **limited memory** \(Q_r\) qubits; a channel through a switch costs **2 qubits**; qubits are **not shared** across channels (Def. 3, Sec. III-A).
- Swapping is **BSM** (two qubits), success probability \(q\); links are Bell pairs with \(p = \exp(-\alpha L)\) (Sec. II-A, Eq. 1).
- Multi-user success is an **entanglement tree**: \(|U|-1\) independent channels, **product** rate \(P = \prod P_A\) (Eq. 2). Infeasible tree \(\Rightarrow P = 0\).
- Routing is **offline**: central planner, then synchronized execution (Sec. II-B). Algorithms 1–4 choose the tree.
- Default eval scale: Waxman (also Watts–Strogatz, Volchenkov), **10 users, 50 switches**, average degree 6, \(Q_r = 4\), \(q = 0.9\), \(\alpha = 10^{-4}\), **20 random graphs**, area \(10\text{k}\times 10\text{k}\) km-units (Sec. V-A).
- Named next steps, **not** in the current eval: **fidelity decay**, **concurrent independent groups** (Intro / Conclusion).

Do **not** score “who is faster on a 1,000-node repeater chain” unless that workload is rebuilt with this model.

---

## How to score

Each metric is **1–5**. Use the anchors. If the feature is undocumented, score from a **matched probe** (same small tree in both tools), not from marketing language.

| Score | Meaning |
|---:|---|
| 5 | Native or a small, documented hook. Paper construct maps 1:1. |
| 4 | Supported with modest custom code; no fight with the kernel. |
| 3 | Possible, but you reimplement a core piece the paper treats as primitive. |
| 2 | Workaround that breaks a paper assumption (e.g. shared qubits, GHZ-only swap). |
| 1 | Not practical without forking internals or changing the problem. |

**Weights**

| Class | Weight | Rule |
|---|---:|---|
| Must | 3 | Any **1** \(\Rightarrow\) not usable to reproduce MUERP. |
| Important | 2 | Needed for a paper-faithful eval or the paper’s own extensions. |
| Nice | 1 | Workflow, scale, inspectability. |

**Composite** (only if no Must-have is 1):

\[
\text{score} = \frac{\sum_i w_i s_i}{\sum_i w_i}
\]

Report the composite **and** the Must-have vector. Do not hide a Must-have 1 behind a high average.

---

## Must-have (weight 3)

These are the paper’s primitives. If a simulator fails here, pick the other one for reproduction.

### M1 — Arbitrary topology, users \(\neq\) switches

**Need:** Import or build undirected \(G=(V,E)\) with a user set \(U\) and switch set \(R\), not only a linear repeater chain. Paper uses Waxman / Watts–Strogatz / Volchenkov and random node placement (Sec. V-A).

| 5 | Load an arbitrary graph; tag nodes as user or switch. |
| 3 | Custom topologies, but users and switches are the same node type. |
| 1 | Chain / grid templates only. |

### M2 — Per-switch capacity and exclusive qubits

**Need:** \(Q_r\) qubits per switch; each channel through a switch **reserves 2 qubits**; those qubits **cannot** sit on another channel at the same time (Def. 3, Sec. III-A). Fiber cores are abundant; **switches** are the bottleneck.

| 5 | Per-node memory size, reservation, and refusal when \(Q_r\) is exhausted. |
| 3 | Memories exist, but exclusivity is left to the user with no resource check. |
| 1 | Infinite memory, or links share a qubit across channels. |

### M3 — BSM swapping with configurable \(q\)

**Need:** Entanglement swapping on **two** qubits (BSM), not n-fusion / GHZ measurement as the only path. Uniform success probability \(q \in [0,1]\) (Sec. II-A). Paper’s claim vs N-FUSION depends on this.

| 5 | Native BSM swap; \(q\) is a parameter. |
| 3 | Swap exists; success is buried in a device model you cannot set to a constant \(q\). |
| 1 | Multipartite fusion only, or no swapping. |

### M4 — Probabilistic Bell links, \(p = \exp(-\alpha L)\)

**Need:** Neighbor entanglement as a Bell pair; link success from **length** and loss constant \(\alpha\) (Sec. II-A). Default \(\alpha = 10^{-4}\).

| 5 | Link generation with length-dependent success; \(\alpha\) and \(L\) are inputs. |
| 3 | Homogeneous \(p\) per edge, you compute \(p\) outside and paste it in. |
| 1 | Deterministic links, or no notion of fiber length. |

### M5 — Inject Algorithms 1–4 (offline tree)

**Need:** A **central planner** computes the entanglement tree, then the network executes it (Sec. II-B). The contribution **is** the routing. Built-in routing must be replaceable.

| 5 | You can pin “which pairs, which paths, which memories” before the run. |
| 3 | Custom protocol, but the stack still allocates paths/memories underneath. |
| 1 | Only the simulator’s own routing / entanglement-management policy. |

### M6 — Export Eq. (1)–(2), including \(P = 0\)

**Need:** Per-channel rate \(P_A = q^{l-1}\prod p_{i,i+1}\) and tree rate \(P = \prod P_A\). If any required channel cannot be built, **\(P = 0\)** (Sec. V-A).

| 5 | Logs or API yield link successes, swap successes, reserved qubits, and you can compute \(P\) without re-deriving the physics. |
| 3 | You can reconstruct \(P\) from traces with extra instrumentation. |
| 1 | Only fidelity / throughput metrics that do not match Eq. (2). |

---

## Important (weight 2)

### M7 — Independent channels (no shared quantum links)

**Need:** Two channels may use the **same fiber** (multi-core) but **not the same qubits** (Sec. III-A). This is why MUERP is not a Steiner tree.

| 5 | Multiple links per fiber; qubit identity is per channel. |
| 3 | One entanglement attempt per edge; you fake parallelism with extra edges. |
| 1 | One shared entangled resource per edge for all pairs. |

### M8 — Multi-user tree, not only pairwise sessions

**Need:** Span \(U\) with \(|U|-1\) channels and **no user-level loops** (Def. 1). Pairwise engines (Q-CAST-style) are the **baseline**, not the native object.

| 5 | First-class multi-party request, or you compose pairwise channels into a tree and score the product. |
| 3 | Pairwise only; tree bookkeeping is entirely outside. |
| 1 | Sessions cannot be composed (e.g. forced GHZ at a hub). |

### M9 — Paper-scale sweeps

**Need:** Default **10 + 50** nodes, degree 6, **20 graph replicas**, sweeps of \(|U|\), \(|R|\), \(D\), \(Q_r\), \(q\), and random edge removal (Sec. V, Figs. 5–8).

| 5 | One replica of the default graph runs in interactive time; 20 replicas × a sweep is batch-feasible. |
| 3 | Default graph runs; full Sec. V sweep is painful but possible. |
| 1 | Even 10 users / 50 switches is not practical. |

### M10 — Match or relax the paper’s timing model

**Need:** Paper assumes **synchronized clocks** and **simultaneous** link generation + swaps in a slot (Sec. II-B). A discrete-event kernel is useful only if you can (a) reproduce that slot model, or (b) **turn on** wait/decoherence as the fidelity extension.

| 5 | You can run both: slotted simultaneous attempts, and timed retries with memory wait. |
| 3 | Timed only; you approximate one slot by ignoring wait. |
| 1 | Timing/decoherence cannot be disabled, so Eq. (1)–(2) are not recoverable. |

---

## Nice-to-have (weight 1)

### M11 — Fidelity / decoherence (named extension)

Paper lists **fidelity decay** as a direct next model (Intro, Conclusion). Score whether memory wait and noisy BSM can degrade fidelity along a channel, not whether a textbook T1/T2 model exists in the abstract.

### M12 — Concurrent independent groups (named extension)

Second named extension: several MUERP instances sharing the same \(Q_r\) pool. Score a **resource manager** that can admit more than one tree without collapsing them into one request.

### M13 — Open internals and protocol hooks

Can you inspect or change entanglement management, memory allocation, and the application layer? SeQUeNCe’s open modules vs NetSquid’s closed internals matter **here** because MUERP **is** a routing/allocation algorithm (`_v0.md`).

### M14 — Matched runtime (not a speed prize)

Wall-clock and peak memory on **the same** graph, \(Q_r\), \(q\), and requested outputs (tree \(P\), occupancy). Sequential vs parallel SeQUeNCe are **separate** configurations (`_v0.md`). Do not treat a 1,000-node repeater number as this score.

### M15 — State representation vs this workload

MUERP’s current eval is **success/fail Bell links + BSM**, not full many-body wavefunctions. Stabilizer / graph / ket that stays cheap on many Bell pairs is a plus; forcing density matrices on 50 switches is a minus. Score fitness to **this** state, not “most representations.”

---

## Scorecard (fill when rating)

| ID | Metric | Class | w | NetSquid (1–5) | SeQUeNCe (1–5) | Evidence (API, doc, probe) |
|---|---|---|---:|---:|---:|---|
| M1 | Topology, users vs switches | Must | 3 |  | 3 | Arbitrary NX → `generate_config` / `RouterNetTopo`. Users and switches are both `QuantumRouter`; tag by name/`memo_size`. |
| M2 | Capacity / exclusive qubits | Must | 3 |  | 5 | Fig. 4a: RSVP takes 2 memories/channel on S. \(Q_S=4\) admits both; \(Q_S=2\) rejects the second. |
| M3 | BSM + configurable \(q\) | Must | 3 |  | 5 | `swapping_success_prob` → `EntanglementSwappingA` (BDS). Fig.~4a physics delivered pairs with $q=0.9$. |
| M4 | Bell links, \(p=\exp(-\alpha L)\) | Must | 3 |  | 4 | `QuantumChannel` length + dB/m loss. Convert \(\alpha\) or compute \(p\) outside. |
| M5 | Inject Algs 1–4 | Must | 3 |  | 4 | Alg. 4 tree pinned; RSVP paths match (`inject_alg4_coherence.md`). Memories still RSVP. |
| M6 | Export Eq. (1)–(2), \(P=0\) | Must | 3 |  | 3 | No native \(P\). Fig. 4a: reject → \(P=0\); else multiply \(p,q\) in the script. |
| M7 | Independent channels | Important | 2 |  | 4 | Fig. 4a Case A: Alice–S shared by two channels; 4 exclusive qubits on S. |
| M8 | Multi-user tree | Important | 2 |  | 3 | Two pairwise `RequestApp`s; tree product is outside. |
| M9 | Paper-scale sweeps | Important | 2 |  | 4 | One 60-node Waxman admission in 0.55 s (`waxman_replica_sequence_results.md`). No 20-replica EG sweep. |
| M10 | Slot timing vs decoherence | Important | 2 |  | 4 | Same Alg. 4 tree: `coherence_time=-1` vs `0.01` s + cutoff. Timed, not slotted. |
| M11 | Fidelity extension | Nice | 1 |  | 4 | Short coherence: 44 `MEMORY_EXPIRED`, 0 pairs vs 7+10 with lifetime off. |
| M12 | Concurrent groups | Nice | 1 |  | 4 | RSVP holds many reservations on one \(Q_r\) pool. Two named MUERP groups not probed. |
| M13 | Open internals | Nice | 1 |  | 5 | Open modules; PyPI 1.3.1. |
| M14 | Matched runtime | Nice | 1 |  | 4 | Waxman replica: 0.55 s, 160 MB RSS. No NetSquid pair. |
| M15 | State representation | Nice | 1 |  | 5 | `bell_diagonal` default for this EG stack. |
| | **Weighted mean** | | |  | **4.00** | SeQUeNCe only. Must vector `[3,5,5,4,4,3]`. NetSquid blank until install. |

---

## Probe before you fill the sheet

Implement **the same** small instance in both (Fig. 4a / glossary example):

- 3 users, 1 switch, equal link success \(p\), swap \(q\).
- Case A: \(Q_S = 4\) \(\rightarrow\) two channels, \(P = (p^2 q)^2\).
- Case B: \(Q_S = 2\) \(\rightarrow\) infeasible, \(P = 0\).

If a tool cannot get both cases right, it fails M2/M6 regardless of architecture essays.

Then, if Must-haves pass, run **one** Waxman replica at the Sec. V-A default and record \(P\), per-switch occupancy, and runtime. That is the only fair speed datapoint.

**SeQUeNCe (2026-11-10):** Fig. 4a admission passed; Alg. 4 tree pinned into RSVP (paths match); coherence off vs on on the same tree. Weighted mean **4.00**. No Must-have is 1. NetSquid still uninstalled — do not apply the decision rule yet.

---

## Decision rule (tied to `_v0.md`)

After scoring:

- If **M5** (custom routing) or **M2** (capacity) is the gap, SeQUeNCe’s resource / entanglement-management modules are the default bet.
- If **M10/M11** (timing, decoherence, fidelity extension) is the gap, NetSquid’s device/timing stack is the default bet.
- If both pass Must-haves, pick on **M13** (need to modify internals) and **M9/M14** (can you actually run the sweep).

A high score means: *this simulator can host MUERP under the paper’s assumptions.* It does not mean it is “more quantum” or universally faster.
