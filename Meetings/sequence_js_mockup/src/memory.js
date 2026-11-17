/**
 * MemoryArray + MemoryTimeCard ≈ a connection pool with a unique constraint.
 *
 * Real SeQUeNCe: each QuantumRouter has memo_size qubit slots. RSVP books
 * a time interval on specific slots. Overlap → insert index -1 → REJECT.
 *
 * MUERP Def. 3: a channel through a switch costs 2 exclusive qubits.
 * Two overlapping channels on S need 4 slots.
 *
 * Mock: we ignore time intervals and just count seats. Fine for Fig. 4a
 * "do both bookings fit right now?"
 */

export class MemoryArray {
  constructor(seatCount) {
    this.seatCount = seatCount;
    this.booked = 0;
    this.reservations = [];
  }

  get freeSeats() {
    return this.seatCount - this.booked;
  }

  /**
   * @returns true if booked (HTTP 200), false if conflict (HTTP 409)
   */
  tryBook(channelId, seatsNeeded) {
    if (this.freeSeats < seatsNeeded) return false;
    this.booked += seatsNeeded;
    this.reservations.push({ channelId, seatsNeeded });
    return true;
  }
}
