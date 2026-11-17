/**
 * muerp.eq2 ≈ an analytics job after checkout.
 *
 * Zeng et al. slot P is NOT a SeQUeNCe metric. After RSVP, a script
 * multiplies p and q. Rejected tree → P = 0.
 *
 * Eq. (1)  P_A = q^(hops - 1) * product(p on each hop)
 * Eq. (2)  P   = product of P_A over the |U|-1 channels
 *
 * Fig. 4a, p = q = 0.9, two length-2 channels:
 *   P_A = 0.9 * 0.9 * 0.9 = 0.729
 *   P   = 0.729 * 0.729   = 0.531441
 *
 * Do not mix this with memory_counter (pairs in a 0.2s retry window).
 * That is RPS. This is "probability the first checkout succeeds."
 */

export function channelRate({ hops, p, q }) {
  let rate = q ** (hops - 1);
  for (let i = 0; i < hops; i++) rate *= p;
  return rate;
}

export function treeRate(reservationResults, { p = 0.9, q = 0.9 } = {}) {
  if (reservationResults.some((r) => !r.ok)) return 0;
  if (reservationResults.length === 0) return 0;

  let pTree = 1;
  for (const r of reservationResults) {
    const hops = r.path.length - 1;
    pTree *= channelRate({ hops, p, q });
  }
  return pTree;
}
