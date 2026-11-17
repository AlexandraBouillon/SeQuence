/**
 * Algorithm 4 — Prim. No Algorithm 2.
 *
 * U1 = {u0}, U2 = everyone else. |U|-1 rounds: among Alg. 1 channels from
 * U1 to U2 that still fit leftover Q_r, take one, move that user into U1,
 * subtract 2 seats per switch. A round with nothing → empty tree, P = 0.
 *
 * Same Fig. 4a numbers as Alg. 3 on this tiny graph; can differ when Q_r
 * is tight on bigger graphs.
 */

import { algorithm1 } from "./algorithm1.js";

export function algorithm4({
  edges,
  users,
  switches,
  qubitsPerSwitch,
  startUser = users[0],
}) {
  const leftover = Object.fromEntries(switches.map((s) => [s, qubitsPerSwitch]));
  const inTree = new Set([startUser]);
  const out = new Set(users.filter((u) => u !== startUser));
  const tree = [];

  const fits = (path) =>
    path.slice(1, -1).every((n) => leftover[n] === undefined || leftover[n] >= 2);

  while (out.size) {
    let best = null;
    for (const ui of inTree) {
      for (const uj of out) {
        const path = algorithm1({
          edges,
          leftoverSeats: leftover,
          from: ui,
          to: uj,
        });
        if (!path || !fits(path)) continue;
        best = { from: ui, to: uj, path };
      }
    }
    if (!best) return [];
    for (const n of best.path.slice(1, -1)) {
      if (leftover[n] !== undefined) leftover[n] -= 2;
    }
    tree.push(best);
    inTree.add(best.to);
    out.delete(best.to);
  }

  return tree;
}
