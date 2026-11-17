/**
 * Fig. 4a as a "full stack" scenario.
 *
 * Spec: Alice, Bob, Carol, switch S. Two channels. 2 seats each on S.
 * Pathfinding (Alg. 4) writes nginx tables. RSVP books. eq2 reports P.
 * Physics is skipped (admission only).
 */

import { fig4aNetwork } from "./topology.js";
import { pinPath } from "./forwarding.js";
import { startTree } from "./requestApp.js";
import { treeRate } from "./eq2.js";
import { runServiceWindow } from "./physics.js";
import { algorithm4 } from "./pathfinding/algorithm4.js";
import { algorithm2 } from "./pathfinding/algorithm2.js";

const USERS = ["alice", "bob", "carol"];
const SWITCHES = ["S"];

function runCase(switchSeats) {
  const net = fig4aNetwork({ switchSeats });

  // Batch job: Prim tree under this Q_r. (Alg. 2 would ignore switchSeats.)
  const tree = algorithm4({
    edges: net.edges,
    users: USERS,
    switches: SWITCHES,
    qubitsPerSwitch: switchSeats,
    startUser: "alice",
  });

  const ignoredCapacityTree = algorithm2({ edges: net.edges, users: USERS });

  for (const ch of tree) pinPath(net.tables, ch.path);

  // carol initiates the second channel so we don't double-start alice.
  const channels = tree.map((ch) => ({ from: ch.from, to: ch.to }));
  const { results } = startTree(net, channels);
  const p = treeRate(results, { p: 0.9, q: 0.9 });
  const physics = runServiceWindow(net);

  return {
    switchSeats,
    alg4Paths: tree.map((ch) => ch.path),
    alg2WouldHaveReturned: ignoredCapacityTree.map((ch) => ch.path),
    forwardingAlice: net.tables.alice,
    rsvp: results.map((r) => ({
      status: r.status,
      path: r.path,
      reason: r.reason || "ok",
    })),
    seatsLeftOnS: net.routers.S.memory.freeSeats,
    slotP: p,
    physics,
  };
}

export function runFig4a() {
  return {
    caseA: runCase(4),
    caseB: runCase(2),
    expected: { caseA: 0.531441, caseB: 0 },
  };
}

export function printFig4a(report = runFig4a()) {
  console.log("=== Fig. 4a mock (not real SeQUeNCe) ===\n");
  console.log("Case A  Q_S=4  (two rooms, four beds)");
  console.log(JSON.stringify(report.caseA, null, 2));
  console.log("\nCase B  Q_S=2  (second booking 409)");
  console.log(JSON.stringify(report.caseB, null, 2));
  console.log("\nExpected slot P:", report.expected);
}

if (process.argv[1]?.endsWith("fig4a.js")) printFig4a();
