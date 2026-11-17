/**
 * Algorithm 2 — Kruskal spanning tree. Ignores small Q_r.
 *
 * Theorem 3: optimal only if every switch has Q_r ≥ 2|U| (enough seats
 * for every possible booking). On Fig. 4a with Q_S = 2 this still returns
 * TWO channels — hardware would 409 the second. That's why Alg. 3 exists.
 */

import { algorithm1 } from "./algorithm1.js";

export function algorithm2({ edges, users }) {
  const leftoverSeats = {}; // empty → Alg. 1 never skips a switch
  const candidates = [];

  for (let i = 0; i < users.length; i++) {
    for (let j = i + 1; j < users.length; j++) {
      const path = algorithm1({
        edges,
        leftoverSeats,
        from: users[i],
        to: users[j],
      });
      if (path) candidates.push({ from: users[i], to: users[j], path });
    }
  }

  // Kruskal: add if users not already connected. Mock: all rates equal, so
  // insertion order is fine.
  const parent = Object.fromEntries(users.map((u) => [u, u]));
  const find = (u) => (parent[u] === u ? u : (parent[u] = find(parent[u])));
  const tree = [];

  for (const ch of candidates) {
    const a = find(ch.from);
    const b = find(ch.to);
    if (a === b) continue;
    parent[a] = b;
    tree.push(ch);
    if (tree.length === users.length - 1) break;
  }

  return tree.length === users.length - 1 ? tree : [];
}
