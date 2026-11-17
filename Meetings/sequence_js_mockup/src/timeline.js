/**
 * Timeline ≈ Node's event loop.
 *
 * Real SeQUeNCe: a discrete-event kernel. Events (photon arrived, RSVP
 * message, memory expired) are scheduled at a simulated time t, not
 * wall-clock Date.now().
 *
 * Mock: a sorted queue of { t, label, fn }. We do NOT model photons.
 * For MUERP *admission* you often never run the queue: you only care
 * whether RSVP returned 200 or 409 (see rsvp.js).
 */

export class Timeline {
  constructor() {
    this.now = 0;
    this.queue = [];
    this.log = [];
  }

  /** Like setTimeout, but in simulated seconds. */
  schedule(delaySeconds, label, fn) {
    this.queue.push({ t: this.now + delaySeconds, label, fn });
    this.queue.sort((a, b) => a.t - b.t);
  }

  /**
   * Zeng et al. want one simultaneous slot. SeQUeNCe is sequential.
   * Admission trick: stop BEFORE t = 1s (the usual EG start), so you
   * never enter the physics window.
   */
  runUntil(stopAt = Infinity) {
    while (this.queue.length && this.queue[0].t <= stopAt) {
      const event = this.queue.shift();
      this.now = event.t;
      this.log.push(`[t=${this.now}] ${event.label}`);
      if (event.fn) event.fn();
    }
  }
}
