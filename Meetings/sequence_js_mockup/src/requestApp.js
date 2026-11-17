/**
 * RequestApp ≈ a pairwise HTTP client, not a multi-user GraphQL mutation.
 *
 * MUERP wants one tree of |U|-1 channels. SeQUeNCe only speaks pairs.
 * Fig. 4a = two clients (Alice–Bob and Alice–Carol), not one
 *   entangle({ alice, bob, carol }).
 *
 * Gotchas copied from the real stack:
 *   - two start() calls on the SAME app object overwrite reservation_result
 *   - if both channels would use alice as initiator, reverse the second
 *     (carol starts toward alice)
 */

import { reserveChannel } from "./rsvp.js";

export class RequestApp {
  constructor(ownerName) {
    this.ownerName = ownerName;
    // Real bug: this field is overwritten by a second start() on the same app.
    this.reservationResult = null;
  }

  start({ routers, tables, to, channelId }) {
    const result = reserveChannel({
      routers,
      tables,
      from: this.ownerName,
      to,
      channelId,
    });
    this.reservationResult = result; // last write wins — don't trust this for two starts
    return result;
  }
}

/**
 * Fig. 4a: two channels. Second initiator is carol so both POSTs are not
 * keyed on alice.
 */
export function startTree(network, channels) {
  const results = [];
  const acceptedOnSwitch = [];

  for (const ch of channels) {
    const app = new RequestApp(ch.from);
    const result = app.start({
      routers: network.routers,
      tables: network.tables,
      to: ch.to,
      channelId: `${ch.from}-${ch.to}`,
    });
    results.push(result);
    if (result.ok) acceptedOnSwitch.push(result);
  }

  return { results, acceptedOnSwitch };
}
