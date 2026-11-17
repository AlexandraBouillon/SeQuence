# Linear repeater chain — SeQUeNCe wall-clock (not MUERP)

Script: `probes/repeater_chain_speed.py`. Linear `QuantumRouter`s, one end-to-end `RequestApp`, \(q=0.9\), 8 memories each, infinite coherence. **Not** the MUERP score (M14). **Not** NetSquid.

Admission stops before the service window. Physics uses a **0.2 s** service window after \(t=1\) s (same window as the four-node star).

| Routers | Hops | Admit wall | Physics wall | Peak RSS | End-to-end pairs in 0.2 s |
|---:|---:|---:|---:|---:|---:|
| 2 | 1 | 0.005 s | 0.019 s | ~155 MB | 1 |
| 5 | 4 | 0.007 s | 0.036 s | ~156 MB | 1 |
| 10 | 9 | 0.011 s | 0.066 s | ~157 MB | 0 |
| 20 | 19 | 0.027 s | 0.155 s | ~155 MB | 0 |
| 50 | 49 | 0.18 s | 0.60 s | ~159 MB | 0 |
| 100 | 99 | 1.02 s | 2.02 s | ~167 MB | 0 |

Most of the time at 50–100 nodes is `RouterNetTopo` construction, not the 0.2 s of entanglement generation. RSVP admitted every chain. Pairs drop to 0 by 10 hops in this short window: that is swap-wait along the chain, not a timeout of the Python process.

Raw: `repeater_chain_speed.json`.
