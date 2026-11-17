# What this writeup is about

The LaTeX file `muerp_sequence_findings.tex` is a lab note, not a textbook.

It asks one question:

> Can an existing quantum-network simulator, **SeQUeNCe 1.3.1**, run the routing problem from Zeng et al. (ICDCS 2024), called **MUERP**?

The short answer: **yes, well enough to host the admission model**, with a weighted score of **4.00 / 5**. Some pieces are native. Some pieces are extra Python next to the simulator.

This page explains the idea, the tiny example, the two numbers people mix up, and what the experiments actually showed.

---

## The everyday problem

Today’s internet sends **copies** of information. A router reads a packet, copies it, and forwards it.

A quantum network cannot do that. A quantum bit (**qubit**) cannot be copied. What you *can* share is a special link called **entanglement**: two qubits that belong together, even if they sit in different cities.

Think of two coins that always land the same way, but you cannot photocopy the coin. You can only make a new linked pair, or **swap** links through a middle station so two far-apart users end up linked.

That middle station is a **switch**. It has a small number of quantum memories, written \(Q_r\) (how many qubits it can hold). Fiber cables are treated as plentiful. **Switch memory is the scarce resource.**

---

## What MUERP is trying to do

**MUERP** means *multi-user entanglement routing*.

Several users want to be connected at once, not just Alice to Bob. Zeng et al. connect them with an **entanglement tree**: enough pairwise links that everyone is in one connected group. For \(n\) users you need \(n-1\) links (the same counting rule as a family tree with no loops).

Rules that matter:

1. Each link that goes through a switch **reserves 2 qubits** there. Those qubits cannot be reused by another link at the same time.
2. If the switch does not have 2 free qubits, that link is refused. Then the whole group fails: success probability \(P = 0\).
3. First, **Algorithms 1–4** (Python code in `muerp/algorithms.py`) pick the tree of paths.
4. Then, in Zeng et al.’s model, every hop and every swap is attempted in **one synchronized slot** — one shared “now.”

SeQUeNCe is a **discrete-event simulator**: a computer program that pretends time is moving and devices are clicking. It already has a reservation system called **RSVP** (“please book these memories for this request”). The lab note checks whether that booking system can play the MUERP rules.

---

## The tiny example (the most important picture)

Three users — Alice, Bob, Carol — and one switch \(S\).

Two links, both length 2 (user → switch → user):

- Alice–Bob through \(S\)
- Alice–Carol through \(S\)

Each link needs **2 qubits** on \(S\). Both links together need **4**.

| Switch memories \(Q_S\) | What happens | Success \(P\) |
|---|---|---|
| 4 | Both links are booked | \(0.531441\) |
| 2 | Only Alice–Bob fits; Alice–Carol is refused | \(0\) |

That is Zeng et al.’s Figure 4a, run inside SeQUeNCe. It is the strongest result in the note: RSVP really does take two exclusive memories per link and refuse the second link when the switch is too small.

If you want a picture: \(S\) has 4 parking spots. Each car (link) needs 2 spots. Two cars fit. One car fits if there are only 2 spots; the second car is turned away.

---

## What the number \(P\) means

\(P\) is **not** “how many pairs we counted this afternoon.”

It is the chance that **the whole tree succeeds in one slot**, if every hop and every swap is tried once.

Each hop succeeds with probability \(p\) (photons can be lost on the fiber). Each swap at a switch succeeds with probability \(q\). For the star, the note sets \(p = q = 0.9\). One length-2 link then succeeds with

\[
p \times p \times q = 0.9^2 \times 0.9 = 0.729
\]

Two independent links both have to work:

\[
P = 0.729 \times 0.729 = 0.531441
\]

If any required link cannot even be reserved, \(P = 0\) by definition.

**SeQUeNCe does not print this \(P\).** A small extra program, `muerp/eq2.py`, multiplies \(p\) and \(q\) after RSVP has accepted or refused the bookings. That is why the score for “export \(P\)” is 3: the formula is reimplemented outside the simulator.

### Do not mix \(P\) with pair counts

In a 0.2 second physics window on the same star, SeQUeNCe *generated* 7 Alice–Bob pairs and 10 Carol–Alice pairs. That is **throughput**: retries over time, like keeping flip-ping coins until the bell rings.

Zeng et al. report the one-shot \(P\). The lab note keeps those two numbers in separate columns on purpose.

---

## Two jobs, two programs

| Job | Who does it |
|---|---|
| Choose the paths (the tree) | Algorithms 1–4 in Python |
| Book memories on the devices | SeQUeNCe RSVP |
| Multiply \(p\) and \(q\) into \(P\) | `muerp/eq2.py` |

That split is why “inject the algorithms” scores **4**, not **5**. The note can overwrite SeQUeNCe’s forwarding tables so RSVP *follows* Alg. 2, 3, or 4. RSVP still decides **which memory slots** to book.

---

## What was actually run

Four kinds of experiment, not mixed together:

1. **Star admission** — the 4-node example above.
2. **Star path pin** — Alg. 4 picks the two paths; those next hops are written into SeQUeNCe; RSVP follows them. With a short memory lifetime, pairs expire (44 expired, 0 delivered). With infinite lifetime, Alice and Carol get 7 and 10 pairs. Booking does not change; only how long qubits are allowed to wait.
3. **Waxman, 10 users + 50 switches** — Zeng et al.’s node count, **one** random graph, two different trees:
   - a dummy spanning tree (load test): all 9 links booked, \(P = 0.0352\)
   - Alg. 2, 3, and 4 (same draw): all 9 links booked, \(P = 0.0197\)
   Those two \(P\) values are different trees. Do not average them.
   Two groups of 5 users can share one memory pool; on this graph both groups fit even at \(Q_r = 2\).
4. **A straight line of 2–100 routers** — a speed check of SeQUeNCe, not a MUERP network. A 100-router line takes about 2 seconds to build and run. In a 0.2 second physics window, end-to-end pairs already drop to 0 by 10 hops, because each swap has to wait for the next.

On the star, generation fidelity averaged **0.90** and swapping fidelity averaged **0.57**. After swaps, the linked pairs are noisier. That is logged from events; it is not Zeng et al.’s slot \(P\).

---

## The grade

Fifteen questions (M1–M15), each scored 1–5:

- **5** = SeQUeNCe already does this
- **4** = a modest extra script is enough
- **3** = you have to reimplement a piece
- **1** = not practical

Must-have questions (M1–M6) are weighted more heavily. A 1 on any must-have would mean “do not use SeQUeNCe for MUERP.” There was no 1.

Must-have scores: **3, 5, 5, 4, 4, 3**. Weighted mean: **4.00**.

In words: SeQUeNCe can book exclusive switch memory the way MUERP requires, follow the Python algorithms’ paths, and run at the 10+50 node size. It does not natively know users vs switches as different device types, and it does not natively report slot \(P\).

---

## What this note is not

- It is not a claim that Zeng et al. were right or wrong about which algorithm is best.
- It is not a comparison against some other simulator.
- It is not “we simulated a real quantum internet.” It is a check that one software kernel can host this routing model on the instances that were run.

If you read the LaTeX next, start with Figure 4a admission, then the star path pin, then the Waxman pin. Those three are the MUERP story. The linear chain is only a stopwatch.
