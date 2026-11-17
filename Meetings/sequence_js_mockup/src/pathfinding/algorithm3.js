/**
 * Algorithm 3 — conflict-free. Alg. 2's candidates, then drop 409s, then reconnect.
 *
 * Walk best-first (here: all equal). Keep a channel only if every switch on
 * it still has ≥ 2 seats; subtract 2. If users remain split, run Alg. 1
 * between different components under leftover Q_r. None found → P = 0.
 */

import { algorithm1 } from "./algorithm1.js";
import { algorithm2 } from "./algorithm2.js";

export function algorithm3({ edges, users, switches, qubitsPerSwitch }) {
  const leftover = Object.fromEntries(switches.map((s) => [s, qubitsPerSwitch]));
  const parent = Object.fromEntries(users.map((u) => [u, u]));
  const find = (u) => (parent[u] === u ? u : (parent[u] = find(parent[u])));
  const tree = [];

  const fits = (path) =>
    path.slice(1, -1).every((n) => leftover[n] === undefined || leftover[n] >= 2);

  const consume = (path) => {
    for (const n of path.slice(1, -1)) {
      if (leftover[n] !== undefined) leftover[n] -= 2;
    }
  };

  for (const ch of algorithm2({ edges, users })) {
    if (!fits(ch.path)) continue;
    if (find(ch.from) === find(ch.to)) continue;
    parent[find(ch.from)] = find(ch.to);
    consume(ch.path);
    tree.push(ch);
  }

  const unions = () => new Set(users.map(find)).size;
  while (unions() > 1) {
    let best = null;
    for (let i = 0; i < users.length; i++) {
      for (let j = i + 1; j < users.length; j++) {
        if (find(users[i]) === find(users[j])) continue;
        const path = algorithm1({
          edges,
          leftoverSeats: leftover,
          from: users[i],
          to: users[j],
        });
        if (!path || !fits(path)) continue;
        best = { from: users[i], to: users[j], path };
      }
    }
    if (!best) return [];
    parent[find(best.from)] = find(best.to);
    consume(best.path);
    tree.push(best);
  }

  return tree;
}
