# SeQUeNCe API map (M1–M6)

Package: `sequence` **1.3.1**, import `sequence as sq`.  
Source of this map: installed modules under `SeQuEnCe/.venv/.../sequence/`, not marketing text.  
**No 1–5 scores.** Probe still required (`rating_metrics.md`).

Docs: [tutorial](https://sequence-rtd-tutorial.readthedocs.io/latest/tutorial/sequence3min/three_minute.html), [network manager](https://sequence-rtd-tutorial.readthedocs.io/latest/tutorial/chapter5/network_manager.html), [RequestApp](https://sequence-rtd-tutorial.readthedocs.io/latest/references/application/request_app.html).

---

## Summary (class / call, or none)

| ID | Paper need | SeQUeNCe hook | Gap for the probe |
|---|---|---|---|
| M1 | Arbitrary \(G=(V,E)\), users \(\neq\) switches | `RouterNetTopo`, `generate_config(nx.Graph)`, `generate-topology` | No User type. `node_type` on graphs is dropped. Users and switches are both `QuantumRouter`. |
| M2 | \(Q_r\), 2 qubits/channel, refuse if exhausted | `memo_size`, `RSVPProtocol.schedule`, `MemoryTimeCard` | Converter sets **one** `memory_size` for every router. Hand-edit JSON for \(Q_S=4\) vs \(Q_S=2\). Refusal exists. |
| M3 | Two-qubit BSM swap, constant \(q\) | `QuantumRouter.swapping_success_prob` → `EntanglementSwappingA` | Paper \(q\) is **swap**, not `SingleHeraldedBSM` (that is link generation). Default \(q=1\). |
| M4 | \(p=\exp(-\alpha L)\) | `QuantumChannel(attenuation, distance)` | Loss is \(1-10^{-att\cdot d/10}\) (dB/m, m). No `p` or \(\alpha\) in the paper’s units. EG protocol is extra physics. |
| M5 | Pin pairs, paths, memories before run | `RequestApp.start` + `update_forwarding_rule` / `set_forwarding_table` | Pairwise only. Path is next-hop table, not an argument. Memories chosen by RSVP, not by the planner. |
| M6 | Eq. (1)–(2), including \(P=0\) | `sequence.utils.metrics` events; `RequestApp.reservation_result` | No \(P=\prod P_A\) metric. Reject → infeasible. Analytic \(P\) is computed outside. |

None of M1–M6 is a hard “none.” Several need small glue (tag users, convert \(\alpha\), set forwarding tables, multiply \(p\) and \(q\) yourself).

---

## M1 — Arbitrary topology, users \(\neq\) switches

### Load / build

| Role | Call |
|---|---|
| Load JSON or dict | `sq.RouterNetTopo(path_or_dict)` |
| NX graph → JSON | `sequence.utils.nx_converter.generate_config(g, cc_delay, memory_size=..., output_file=..., output_directory=...)` |
| CLI templates | `generate-topology linear\|star\|waxman\|grid\|...` |
| Arbitrary GML | `generate-topology custom path.gml` |
| Waxman | `sequence.utils.graphs.build_waxman(nodes, area_size=..., attenuation=..., seed=...)` then `generate_config` |

`RouterNetTopo._add_nodes` accepts only `"QuantumRouter"` and `"BSMNode"`. Anything else raises `ValueError`.

Paper Watts–Strogatz / Volchenkov: **not** in the CLI. Build with NetworkX (or by hand), then `generate_config`.

### Users vs switches

`graphs.py` tags NX nodes `"processing"` vs `"switch"` and documents switches as non-endpoints. **`generate_config` ignores `node_type`.** Every graph vertex becomes a `QuantumRouter` named `router_{i}`. `BSMNode`s are extra mid-link nodes for meet-in-the-middle generation, not the paper’s switches.

There is no `User` class. `sq.Switch` is an optical hardware component, not a network switch.

**How to tag roles for MUERP**

1. Name routers (`alice`, `bob`, `carol`, `S`) in a hand-written config, or keep the `graph_to_name` map from `generate_config`.
2. Attach `sq.RequestApp` only to user routers.
3. Set `memo_size` large on users (paper: users have enough capacity) and \(Q_r\) on switches.

`build_star(3)` is the Fig. 4a shape (center + 3 leaves) but still emits four `QuantumRouter`s with the same `memo_size`.

---

## M2 — Per-switch capacity and exclusive qubits

| Paper | Call |
|---|---|
| \(Q_r\) qubits on a switch | `QuantumRouter(..., memo_size=Q_r)` or JSON `"memo_size"` |
| Array of memories | `MemoryArray(..., num_memories=memo_size)` |
| Request width (pairs at each endpoint) | `RequestApp.start(..., memo_size=1)` → `Reservation.memory_size` |
| 2 qubits at an intermediate switch | `RSVPProtocol.schedule`: initiator/responder reserve `memory_size`; **other nodes reserve `memory_size * 2`** |
| Exclusive / no overlap | `MemoryTimeCard.add` / `schedule_reservation`; overlapping interval → insert index `-1` |
| Refuse when exhausted | `schedule` returns `False` → `RSVPMsgType.REJECT` → `RequestApp.get_reservation_result(..., False)` |

So one pair (`memory_size=1`) through a switch costs **2** memories on that switch, matching Def. 3.

Two overlapping channels on the same switch both need 2 memories → need `memo_size >= 4` (Case A). `memo_size=2` should reject the second reservation (Case B). **This is the probe.** Do not score M2 until both cases run.

`generate_config(..., memory_size=N)` writes the **same** `memo_size` on every router. For Fig. 4a, write the JSON (or post-edit): users large, `S` is 4 or 2.

---

## M3 — BSM swapping with configurable \(q\)

Paper \(q\) is **entanglement swapping** at the switch, not photon BSM on the fiber.

| Role | Call |
|---|---|
| Constant \(q\) on a router | JSON template `"EntanglementSwapping": {"swapping_success_prob": 0.9}` **or** `router.swapping_success_prob = 0.9` after load |
| Protocol | `EntanglementSwappingA.create(..., success_prob=...)` via `es_rule_action_A` |
| Coin flip | `owner.get_generator().random() < self.success_prob` (`swapping_circuit.py` / `swapping_bds.py`) |

Default `swapping_success_prob` is **1**. Tutorial `RSVPProtocol.set_swapping_success_rate` **does not exist** in 1.3.1.

`SingleAtomBSM` / `SingleHeraldedBSM` live on `BSMNode` and serve **link generation** (Barrett–Kok or single-heralded). Detector `efficiency` is not paper \(q\).

Swapping is two `Memory` objects on the interior router (two qubits). That matches the paper’s two-qubit swap, as a parameterized success probability rather than an explicit BSM circuit you set to \(q\).

---

## M4 — Probabilistic Bell links, \(p = \exp(-\alpha L)\)

| Role | Call |
|---|---|
| Fiber | `QuantumChannel(name, timeline, attenuation, distance)` |
| JSON | `"qchannels": [{"source", "destination", "distance", "attenuation"}]` |
| NX edge attrs | `length` (km), `attenuation` (dB/m) |
| Loss used at runtime | `QuantumChannel.init`: `self.loss = 1 - 10 ** (self.distance * self.attenuation / -10)` with `distance` in **meters**, `attenuation` in **dB/m** |

There is **no** `p`, **no** \(\alpha\) in paper units, and **no** `success_probability` on the channel.

`generate_config` splits each NX edge: `to_bsm_dist = length_km * 1000 / 2` meters to the mid-link `BSMNode`.

Paper: \(p = \exp(-\alpha L)\) with \(\alpha=10^{-4}\), \(L\) in km-units. To match transmittance \(T=10^{-att\cdot d/10}\) to \(\exp(-\alpha_{\text{paper}} L_{\text{km}})\) you convert \(\alpha\) once, or you compute \(p\) outside and back-solve `attenuation`.

Link generation is still a protocol (`BarretKokA` two rounds, or `SingleHeraldedA`; default template is `single_heralded`). Realized EG success is **not** exactly channel transmittance. For Eq. (1), treat \(p\) as an input you set via attenuation (and, if needed, detector/memory efficiency), or skip photon MC and multiply \(p\) analytically (M6).

---

## M5 — Inject Algorithms 1–4 (offline tree)

| Role | Call |
|---|---|
| Pairwise request | `app = sq.RequestApp(user_router)`; `app.start(responder, start_t, end_t, memo_size, fidelity)` |
| Internal | `QuantumRouter.reserve_net_resource` → `NetworkManager.request` → `RSVPProtocol.push` |
| Default path | `RouterNetTopo._generate_forwarding_table`: Dijkstra → `StaticRoutingProtocol.update_forwarding_rule(dst, next_hop)` |
| Override next hop | `router.network_manager.get_routing_protocol().update_forwarding_rule(dst, next_hop)` |
| Override whole table | `router.network_manager.set_forwarding_table({dst: next_hop, ...})` |
| Path after admit | `Reservation.set_path(path)` (RSVP writes this; `RequestApp.path` copies it) |

`RequestApp.start` has **no path argument**. RSVP walks the forwarding table hop by hop and builds `path` from `QCap`s. Memories are assigned by `RSVPProtocol.schedule` onto `MemoryTimeCard`s, not by the planner.

To inject a MUERP tree:

1. Run Algs 1–4 **outside** SeQUeNCe (not required for Fig. 4a).
2. For each channel (user pair + path), set forwarding rules so RSVP follows that path.
3. Call `RequestApp.start` on the initiator with the same `start_t`/`end_t` as the other channels.
4. RSVP still admits/refuses and picks which memory indices.

The stack therefore still allocates paths (unless you overwrite the table) and memories. `DistributedRoutingProtocol` is the other built-in; do not use it for an offline planner.

Fig. 4a needs two `start` calls (Alice–Bob, Alice–Carol), not a multi-party request object.

---

## M6 — Export Eq. (1)–(2), including \(P=0\)

No built-in \(P_A = q^{l-1}\prod p_{i,i+1}\) or \(P=\prod P_A\).

| Ingredient | Hook |
|---|---|
| Enable logs | `from sequence.utils import metrics`; `metrics.register_time_provider(tl)`; `metrics.enable([...])` |
| Link attempts | `EventTypes.EG_SUCCESS` / `EG_FAILURE`; `EG_METRIC` |
| Swap attempts | `EventTypes.ES_SUCCESS` / `ES_FAILURE`; `ES_METRIC` |
| Reservation outcome | `RESERVATION_APPROVED` / `REJECTED` / `HOP_REJECT`; `RequestApp.reservation_result` |
| Occupancy | `EventTypes.MEMORY_UPDATE`; `MEMORY_UTILIZATION_RATIO_METRIC` |
| Delivered pairs | `EventTypes.DELIVERY`; `THROUGHPUT_METRIC` (rate, not Eq. (2)) |
| Dump | `metrics.collect_trial_metrics(node_name)`; `metrics.storage.get_by_event(...)` |

**\(P=0\):** if any required channel’s reservation is rejected, treat the tree as infeasible. That is the Case B signal.

**Analytic \(P\):** after admission, compute \(P_A\) from your chosen \(p\) (from \(L,\alpha\) or from channel `loss`) and \(q=`swapping_success_prob`**, product over channels. Do not use Monte Carlo throughput as Eq. (2).

---

## Fig. 4a probe — suggested SeQUeNCe objects

Do not implement this here; this is the call list for the next step.

1. Four `QuantumRouter`s: `alice`, `bob`, `carol`, `S`. Three mid-link `BSMNode`s. Star fibers.
2. Users: large `memo_size`. `S`: Case A `memo_size=4`, Case B `memo_size=2`.
3. Template: `"EntanglementSwapping": {"swapping_success_prob": q}` (e.g. 0.9).
4. Set `attenuation`/`distance` so each user–S link has the same \(p\), **or** compute \(p\) analytically and skip matching MC.
5. Forwarding: `alice → S → bob`, `alice → S → carol`.
6. Two `RequestApp.start` calls, same time window, `memo_size=1`.
7. Case A: both `reservation_result is True`; \(P=(p^2 q)^2\).
8. Case B: second request rejected (or first-only tree cannot span \(U\)); \(P=0\).

---

## What this map is not

- Not a filled scorecard.
- Not Algorithms 1–4.
- Not a NetSquid map (still empty `NetSqid/`).
