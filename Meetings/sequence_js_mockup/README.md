# SeQUeNCe as a JS app (learning mock)

This directory is a **cartoon** of SeQUeNCe + MUERP in the language of a JS full-stack app.
It is **not** the real simulator. Physics is a stub. Names match `sequence_for_js_devs.md`.

```bash
cd Meetings/sequence_js_mockup
node src/index.js      # architecture tour + Fig. 4a
node src/fig4a.js      # just the two booking cases
```

No `npm install`. Node 18+ ESM.

## Map to the real stack

| This folder | Real SeQUeNCe / MUERP | Your usual JS |
|---|---|---|
| `src/timeline.js` | `Timeline` | Node event loop / `setTimeout` |
| `src/topology.js` | `RouterNetTopo` / `generate_config` | k8s / docker-compose |
| `src/router.js` | `QuantumRouter` | one microservice instance |
| `src/memory.js` | `MemoryArray` + `MemoryTimeCard` | connection pool + unique index |
| `src/forwarding.js` | static routing tables | nginx `proxy_pass` |
| `src/rsvp.js` | `RSVPProtocol` | `POST /reservations` → 200 / 409 |
| `src/requestApp.js` | `RequestApp` | HTTP client for one pair |
| `src/eq2.js` | `muerp.eq2` | analytics job after checkout |
| `src/physics.js` | EG / ES | device layer you skip for admission |
| `src/pathfinding/` | Algorithms 1–4 | OSRM / Dijkstra worker |
| `src/fig4a.js` | findings Fig. 4a probe | one product scenario |

## Data flow (same as the markdown)

```
pathfinding worker  →  write nginx tables  →  RSVP 200/409  →  optional physics  →  eq2 report
```

Algorithms live **outside** the runtime. The runtime only books seats and (optionally) retries.
