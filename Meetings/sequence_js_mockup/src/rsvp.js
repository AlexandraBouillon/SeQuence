/**
 * RSVP ≈ POST /reservations with a row lock.
 *
 * Real SeQUeNCe walks the forwarding-table path:
 *   - initiator / responder book memory_size (usually 1)
 *   - every INTERMEDIATE books 2× that   ← MUERP's "2 qubits per channel"
 *   - MemoryTimeCard overlap → REJECT (409)
 *
 * Algorithms 1–4 do not pick which seat ids. RSVP does (your ORM).
 */

import { resolvePath } from "./forwarding.js";

export function reserveChannel({ routers, tables, from, to, channelId }) {
  const path = resolvePath(tables, from, to);
  if (!path) {
    return { ok: false, status: 404, reason: "no path in forwarding table", path: null };
  }

  const seatsByRouter = {};
  for (let i = 0; i < path.length; i++) {
    const name = path[i];
    const isEndpoint = i === 0 || i === path.length - 1;
    seatsByRouter[name] = isEndpoint ? 1 : 2;
  }

  // Check all seats first (atomic booking). Real RSVP can reject mid-path.
  for (const [name, seats] of Object.entries(seatsByRouter)) {
    if (routers[name].memory.freeSeats < seats) {
      return {
        ok: false,
        status: 409,
        reason: `${name} needs ${seats} seats, has ${routers[name].memory.freeSeats}`,
        path,
      };
    }
  }

  for (const [name, seats] of Object.entries(seatsByRouter)) {
    routers[name].memory.tryBook(channelId, seats);
  }

  return { ok: true, status: 200, path, seatsByRouter };
}
