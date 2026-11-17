# NetSquid API map (M1–M6)

**Status:** doc-only. `NetSqid/` is empty; `docs.netsquid.org` and `netsquid.org` timed out from this environment. Hooks below are from the [Nature 2021 paper](https://www.nature.com/articles/s42005-021-00647-8) + SI, public tutorials, and the standard `netsquid` package layout. **Verify each call after install.** No 1–5 scores.

Install (not done): register at netsquid.org, then typically `pip install netsquid` against their index into `/Users/alexandrabouillon/Documents/Quantum_Networking/NetSqid/.venv`. Closed source; internals cannot be patched.

---

## Summary (class / call, or none)

| ID | Paper need | NetSquid hook | Gap for the probe |
|---|---|---|---|
| M1 | Arbitrary \(G=(V,E)\), users \(\neq\) switches | `Network`, `Node`, `add_connection` from a graph | No User vs Switch type. Role = name + `QuantumProcessor(num_positions=...)`. |
| M2 | \(Q_r\), 2 qubits/channel, refuse if exhausted | `QuantumProcessor(num_positions=Q_r)` / `QuantumMemory` | **No reservation protocol.** Exclusivity is your code. Positions exist; refusal is not native. |
| M3 | Two-qubit BSM swap, constant \(q\) | `QuantumProgram` + Bell measure (e.g. `INSTR_MEASURE_BELL` or CNOT/H/measure) | No `q` field on a switch. Put \(q\) in a `NodeProtocol` coin-flip, or a noisy instruction model. |
| M4 | \(p=\exp(-\alpha L)\) | `FibreLossModel(p_loss_init, p_loss_length)` on `QuantumChannel` | Loss is \((1-P_{\mathrm{init}})10^{-\alpha_{\mathrm{dB}} L/10}\), not \(\exp(-\alpha L)\). Or `QSource` with a constant success probability. |
| M5 | Pin pairs, paths, memories before run | `NodeProtocol` / `LocalProtocol` you write | No RSVP / network manager. Planner **is** your protocol. Kernel will not allocate a path underneath. |
| M6 | Eq. (1)–(2), including \(P=0\) | `DataCollector`; your own logs | No \(P=\prod P_A\). \(P=0\) only if **you** refuse the tree. |

M2 is the weak primitive: memory slots exist, admission does not.

---

## M1 — Arbitrary topology, users \(\neq\) switches

| Role | Call (verify after install) |
|---|---|
| Reset engine | `import netsquid as ns`; `ns.sim_reset()` |
| Graph of nodes | `from netsquid.nodes import Network, Node`; `network = Network("muerp")`; `network.add_nodes([Node(name) for name in names])` |
| Quantum + classical fiber | `from netsquid.components import QuantumChannel, ClassicalChannel`; `network.add_connection(n1, n2, channel_to=..., channel_from=..., length=L)` |
| From NetworkX | Loop `G.edges`; there is no `generate-topology` equivalent in core NetSquid |

No `User` / `Switch` class. Paper \(U\) vs \(R\): give user nodes and switch nodes different names and different `num_positions`. Star for Fig. 4a is four `Node`s plus six directed quantum channels (or three `Connection`s).

---

## M2 — Per-switch capacity and exclusive qubits

| Role | Call |
|---|---|
| \(Q_r\) slots | `from netsquid.components import QuantumProcessor`; `QuantumProcessor(f"{name}_proc", num_positions=Q_r)` then `node.add_subcomponent(proc)` or `Node(..., qmemory=proc)` |
| Use a slot | `qmemory.mem_positions[i]`, `qmemory.put`, `qmemory.pop` / `execute_instruction` |

There is **no** analogue of `RSVPProtocol.schedule` / `MemoryTimeCard`. Overlapping channels share positions unless you track reservations yourself (a dict of slot → channel, refuse when fewer than 2 free slots).

For Fig. 4a: processor with 4 vs 2 positions on S is the hardware; **admission** is custom. Until that check exists and Case B returns \(P=0\), do not treat M2 as native.

---

## M3 — BSM swapping with configurable \(q\)

| Role | Call |
|---|---|
| Two-qubit swap on S | `from netsquid.components.qprogram import QuantumProgram`; `from netsquid.components import instructions as instr` |
| Bell measure | `self.apply(instr.INSTR_MEASURE_BELL, [q1, q2])` inside a `QuantumProgram` (confirm symbol after install); fallback: CNOT + H + two `INSTR_MEASURE` |
| Constant \(q\) | In `NodeProtocol`: if `rng.random() > q: fail` **or** a custom instruction noise model |

Paper \(q\) is a uniform success probability, not T1/T2. NetSquid will happily run a physically detailed BSM; for MUERP you should **not** bury \(q\) in detector dark counts. Set \(q\) as a protocol parameter.

---

## M4 — Probabilistic Bell links, \(p=\exp(-\alpha L)\)

| Role | Call |
|---|---|
| Length-dependent loss | `from netsquid.components.models.qerrormodels import FibreLossModel`; `QuantumChannel(..., models={"quantum_loss_model": FibreLossModel(p_loss_init=0, p_loss_length=alpha_dB_per_km)}, length=L_km)` |
| Delay | `FibreDelayModel` / `FixedDelayModel` |
| Homogeneous \(p\) | `QSource` + `StateSampler` of a Bell pair, fire with probability \(p\); or `FixedLossModel` if present |

Published fibre formula: survival \((1-P_{\mathrm{init}})\times 10^{-\alpha_{\mathrm{loss}} L/10}\). Same mismatch as SeQUeNCe: convert \(\alpha\), or compute \(p=\exp(-\alpha L)\) outside and paste it into a source/success Bernoulli.

---

## M5 — Inject Algorithms 1–4 (offline tree)

| Role | Call |
|---|---|
| Protocol base | `from netsquid.protocols import NodeProtocol, LocalProtocol, Protocol` |
| Time | `ns.sim_run()`, `yield self.await_timer(...)`, `yield self.await_port_input(...)` |
| Pin path / memories | Your protocol’s constructor arguments: list of node names, list of memory indices |

No built-in routing stack. Dijkstra will not run unless you write it. That is the right shape for an offline MUERP planner: compute the tree in Python, pass channels into protocols, execute.

Fig. 4a: two `NodeProtocol`s (Alice–Bob, Alice–Carol) that reserve two positions on S each.

---

## M6 — Export Eq. (1)–(2), including \(P=0\)

| Role | Call |
|---|---|
| Time series | `from netsquid.util.datacollector import DataCollector` |
| Counters | Python ints in the protocol; `protocol.get_signal_result` |

No Eq. (1)–(2). After your admission logic: rejected channel → tree \(P=0\); admitted tree → \(P=\prod_A q^{l-1}\prod p_{i,i+1}\) in the script. Same analytic product as SeQUeNCe.

---

## Fig. 4a — suggested NetSquid objects (not implemented)

1. `Network` with nodes `alice`, `bob`, `carol`, `S`.
2. `QuantumProcessor` on users (large `num_positions`); on `S`: 4 vs 2.
3. Three connections with the same \(L\) / same \(p\).
4. Custom admission: each channel needs 2 free positions on `S`; Case B refuses the second channel.
5. Swap protocol on `S` with parameter `q`.
6. Analytic \(P=(p^2 q)^2\) or \(0\).

Do **not** score until this probe runs against an installed `netsquid`.

---

## What this map is not

- Not a filled scorecard.
- Not an installed-package citation (unlike `sequence_api_map_m1_m6.md`).
- Not Algorithms 1–4.
