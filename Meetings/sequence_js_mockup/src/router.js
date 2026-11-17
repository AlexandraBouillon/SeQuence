/**
 * QuantumRouter ≈ one microservice instance.
 *
 * Real SeQUeNCe: users AND switches are this same class. There is no User
 * type. sq.Switch is a NIC, not "the switch service."
 *
 * You tag roles like k8s labels: name + memo_size.
 *   alice/bob/carol → large pool (users have "enough")
 *   S               → Q_r = 4 or 2
 */

import { MemoryArray } from "./memory.js";

export class QuantumRouter {
  constructor(name, { memoSize, role }) {
    this.name = name;
    this.role = role; // "user" | "switch"  — our label, not a SeQUeNCe type
    this.memory = new MemoryArray(memoSize);
  }
}
