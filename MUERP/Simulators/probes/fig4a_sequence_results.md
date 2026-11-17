# Fig. 4a probe — SeQUeNCe (passed)

Ran `fig4a_sequence.py` with SeQUeNCe 1.3.1. Admission only (timeline stop 0.1 s, before the service window). Analytic \(P\), not Monte Carlo throughput.

Roles: `router_0` = switch S, `router_1` = Alice, `router_2` = Bob, `router_3` = Carol.  
Channels: Alice–Bob and Alice–Carol, each path length 2 (one swap). \(p=0.9\), \(q=0.9\).

| Case | \(Q_S\) | Admitted | Memories reserved on S | \(P\) | Expected |
|---|---:|---|---:|---:|---:|
| A | 4 | Alice–Bob **and** Alice–Carol | 4 / 4 | \( (0.9^2\cdot 0.9)^2 = 0.531441 \) | same |
| B | 2 | Alice–Bob only; Alice–Carol **rejected** | 2 / 2 | \(0\) | \(0\) |

Paths when admitted: `router_1 → router_0 → router_2` and `router_1 → router_0 → router_3`.

**M2:** Intermediate RSVP takes 2 memories per channel. \(Q_S=4\) holds both; \(Q_S=2\) refuses the second. Qubits are not shared.

**M6:** No Eq. (2) metric in the engine. Script sets \(P=0\) if any required channel is rejected, else \(P=(p^2 q)^2\).

**Do not** use a single `RequestApp.reservation_result` for two overlapping starts on Alice: the flag is overwritten by whichever RSVP reply arrives last. Use `switch.network_manager.rsvp.accepted_reservations`.

JSON configs: `fig4a_qs4.json`, `fig4a_qs2.json`. Raw dump: `fig4a_sequence_results.json`.

NetSquid Fig. 4a is **not** run (`NetSqid/` empty). SeQUeNCe column of `rating_metrics.md` is filled; NetSquid column stays blank.
