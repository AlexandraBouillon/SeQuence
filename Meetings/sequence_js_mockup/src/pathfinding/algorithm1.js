/**
 * Algorithm 1 — max-rate path for ONE pair. Your shortestPath(from, to).
 *
 * Real math: Dijkstra on weight (αL − ln q) so a PRODUCT of hop/swap
 * success becomes a SUM. Skip a switch neighbor with fewer than 2 free seats.
 *
 * Mock: unweighted BFS on the fiber graph. Enough to see "this is a
 * pure function, no Timeline, no HTTP."
 */

export function algorithm1({ edges, leftoverSeats, from, to }) {
  if (from === to) return null;

  const neighbors = adjacency(edges);
  const prev = {};
  const seen = new Set([from]);
  const queue = [from];

  while (queue.length) {
    const here = queue.shift();
    if (here === to) break;
    for (const hop of neighbors.get(here) || []) {
      if (seen.has(hop)) continue;
      // Paper: skip switch uh if Q_uh < 2. Users have no leftoverSeats entry.
      if (leftoverSeats[hop] !== undefined && leftoverSeats[hop] < 2) continue;
      seen.add(hop);
      prev[hop] = here;
      queue.push(hop);
    }
  }

  if (!(to in prev)) return null;

  const path = [to];
  let walk = to;
  while (walk !== from) {
    walk = prev[walk];
    path.push(walk);
  }
  path.reverse();
  return path;
}

export function adjacency(edges) {
  const map = new Map();
  for (const [a, b] of edges) {
    if (!map.has(a)) map.set(a, []);
    if (!map.has(b)) map.set(b, []);
    map.get(a).push(b);
    map.get(b).push(a);
  }
  return map;
}
