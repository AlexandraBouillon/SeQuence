# Alg. 4 → SeQUeNCe RSVP, then coherence off vs on

Ran `muerp/inject_alg4_coherence.py` (SeQUeNCe 1.3.1). Fig. 4a star: `router_0` = switch S, users `router_1,2,3`. Planner is Alg. 4; kernel is RSVP + single-heralded EG / Bell-diagonal swap. Slot \(P\) uses \(p=q=0.9\) as in Fig. 4a, **not** `memory_counter`.

Alg. 4’s own `rate` on this NX star used \(L=10\,\mathrm{m}\) (\(\alpha=10^{-4}\)), so \(p\approx 1\) and the planner product is \(0.807\). That is **not** Eq. (2) for the paper instance. Reported \(P\) below is \((p^2 q)^{|A|}\) with \(p=0.9\).

## Admission (service window not started)

| Case | \(Q_S\) | Alg. 4 tree | RSVP | Paths match pin? | \(P\) |
|---|---:|---|---|---|---:|
| A | 4 | 1–0–2 and 1–0–3 | both accepted | **yes** | \(0.531441\) |
| B | 2 | empty (hub would need 4 qubits) | no starts | n/a (planner refused) | \(0\) |

Pinned then reserved (Case A): `router_1 → router_0 → router_2` and `router_3 → router_0 → router_1` (second initiator flipped so two `RequestApp`s do not share Alice).

**M5:** Forwarding tables can be cleared and pinned to Alg. 4 next-hops; RSVP follows those paths. RSVP still chooses memory indices (`MemoryTimeCard`). Score stays 4, not 5.

**M2:** Alg. 4 with \(Q_S=2\) returns no tree (\(P=0\)). That is the planner form of Fig. 4a Case B; sequential RSVP rejection of a second channel was already measured in `fig4a_sequence.py`.

## Physics, \(Q_S=4\), \(0.2\,\mathrm{s}\) window after \(t=1\,\mathrm{s}\)

| Setting | EG success | ES success | `MEMORY_EXPIRED` | initiator counters | wall |
|---|---:|---:|---:|---|---:|
| coherence off (`coherence_time=-1`, `cutoff_flag=False`) | 80 | 18 | 0 | Alice 7, Carol 10, Bob 0 | \(0.068\,\mathrm{s}\) |
| coherence on (`0.01\,\mathrm{s}`, `cutoff_flag=True`) | 84 | 13 | **44** | **all 0** | \(0.067\,\mathrm{s}\) |

Bob’s counter is 0 because Bob is the responder on Alice–Bob; `RequestApp.memory_counter` lives on the initiator. Deliveries with coherence off match the earlier unpaired physics run.

**M10:** Same tree, decoherence off (infinite lifetime) vs on (cutoff). Kernel is still timed, not a slotted simultaneous attempt, so not a 5.

**M11:** Short coherence + cutoff zeros delivered pairs (44 expiries). That is wait-to-kill, not a logged fidelity trajectory along the channel.

Raw dump: `inject_alg4_coherence.json`.
