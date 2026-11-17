/**
 * Architecture tour, then Fig. 4a.
 *
 * Layers, top to bottom:
 *   pathfinding/   pure functions (Algorithms 1–4)
 *   forwarding.js  nginx tables
 *   requestApp.js  pairwise clients
 *   rsvp.js        booking API 200 / 409
 *   memory.js      seat pool
 *   topology.js    docker-compose from a graph
 *   timeline.js    event loop (unused for admission)
 *   physics.js     skipped device layer
 *   eq2.js         analytics job → slot P
 */

import { printFig4a, runFig4a } from "./fig4a.js";

console.log(`
SeQUeNCe JS mock — read src/* comments, then this output.

  [pathfinding worker]  Alg. 1–4  →  list of paths + formula P
           │
           ▼
  [nginx tables]        pinPath()  — RequestApp has no path: argument
           │
           ▼
  [booking API]         RSVP  200 or 409   (2 seats per channel on S)
           │
           ▼
  [analytics]           eq2.treeRate()     slot P, not RPS
           │
           ▼
  [optional k6]         physics.js         skipped for admission

Real SeQUeNCe never calls Algorithms 1–4. You configure it after they run.
`);

printFig4a(runFig4a());
