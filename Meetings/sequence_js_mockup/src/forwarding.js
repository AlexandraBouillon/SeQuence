/**
 * Forwarding table ≈ nginx proxy_pass / API-gateway next hop.
 *
 * Real SeQUeNCe: RequestApp.start({ to: "bob" }) has NO path argument.
 * Packets follow whatever next-hop map is on each router.
 *
 * Algorithms 1–4 (pathfinding/) compute the path. You overwrite these
 * tables, then start apps. If you skip that step, SeQUeNCe uses its own
 * static routing — that is not MUERP.
 */

export function emptyTables(routerNames) {
  const tables = {};
  for (const name of routerNames) tables[name] = {};
  return tables;
}

/** Walk next hops from `from` until `to` (or give up). */
export function resolvePath(tables, from, to, maxHops = 16) {
  const path = [from];
  let here = from;
  for (let i = 0; i < maxHops; i++) {
    if (here === to) return path;
    const next = tables[here]?.[to];
    if (!next) return null;
    path.push(next);
    here = next;
  }
  return null;
}

/**
 * Pin a bidirectional path, e.g. ["alice", "S", "bob"].
 * Real code also writes the reverse so RSVP can signal back.
 */
export function pinPath(tables, nodeSequence) {
  const dest = nodeSequence[nodeSequence.length - 1];
  const src = nodeSequence[0];
  for (let i = 0; i < nodeSequence.length - 1; i++) {
    tables[nodeSequence[i]][dest] = nodeSequence[i + 1];
  }
  for (let i = nodeSequence.length - 1; i > 0; i--) {
    tables[nodeSequence[i]][src] = nodeSequence[i - 1];
  }
}
