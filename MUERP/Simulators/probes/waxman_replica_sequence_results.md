# One Waxman replica — SeQUeNCe (admission)

Paper-scale **load + RSVP**, not Algorithms 1–4 and not Monte Carlo entanglement.

| Item | Value |
|---|---|
| Graph | Waxman, 60 nodes (10 users `router_0`–`router_9`, 50 switches), area \(10^4\times 10^4\), seed 0 |
| Tuned NX params | \(\alpha=0.15\), \(\beta=0.8\), **mean degree 6.33** (190 edges) |
| Hardware | \(Q_r=4\) on switches, 32 memories on users, \(q=0.9\) |
| Tree | MST of shortest-path distances among users (**9 channels**, not Algs 1–4) |
| Admitted | **9 / 9** |
| Analytic \(P\) | \(0.0352\) (Eq. (2) with \(p_e=\exp(-10^{-4} L_{\mathrm{km}})\)) |
| Switch occupancy | max **2 / 4**, sum 18, **0 saturated** |
| Wall-clock | graph 0.03 s, `RouterNetTopo` **0.50 s**, init 0.01 s, RSVP **0.004 s**, total **0.55 s** |
| Peak RSS | **160 MB** |

Dummy tree happened to fit in \(Q_r=4\). A paper algorithm that packs more channels through hubs would stress refusal the way Fig. 4a Case B did.

This is M9/M14 for **SeQUeNCe admission only**. Full EG over 1–2 s of simulated time is not run.
