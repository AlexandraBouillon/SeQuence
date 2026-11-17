/**
 * Entanglement generation / swapping ≈ a device layer you skip for admission.
 *
 * Real SeQUeNCe: after t = 1s, photons fly, swaps run, memories expire.
 * Loss is dB/m, not p = exp(-αL). Default swapping_success_prob is 1, not 0.9.
 *
 * For "does the MUERP tree fit?" you stop the timeline before this file.
 * Running it is a load test (k6), not the spec's P.
 */

export function runServiceWindow(_network, { seconds = 0.2 } = {}) {
  return {
    skipped: true,
    reason:
      "Admission only: physics window not run. Real SeQUeNCe would retry EG/ES here and increment memory_counter.",
    windowSeconds: seconds,
    fakeThroughput: { aliceBob: null, aliceCarol: null },
  };
}
