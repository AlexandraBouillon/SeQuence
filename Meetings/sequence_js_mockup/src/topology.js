/**
 * generate_config / RouterNetTopo ≈ docker-compose up from a graph.
 *
 * Real SeQUeNCe turns every NX vertex into a QuantumRouter. Mid-link
 * BSMNodes (photon hardware) are extra boxes — not MUERP switches.
 *
 * Fig. 4a product shape: star with S in the middle, three users around it.
 */

import { QuantumRouter } from "./router.js";
import { emptyTables } from "./forwarding.js";

export function fig4aNetwork({ switchSeats }) {
  const routers = {
    S: new QuantumRouter("S", { memoSize: switchSeats, role: "switch" }),
    alice: new QuantumRouter("alice", { memoSize: 32, role: "user" }),
    bob: new QuantumRouter("bob", { memoSize: 32, role: "user" }),
    carol: new QuantumRouter("carol", { memoSize: 32, role: "user" }),
  };

  // Undirected fiber. length is whatever Zeng et al. use; eq2.js only needs p.
  const edges = [
    ["alice", "S"],
    ["bob", "S"],
    ["carol", "S"],
  ];

  return {
    routers,
    edges,
    tables: emptyTables(Object.keys(routers)),
  };
}
