# Rubric and weights (MUERP host score)

This is the scoring sheet used in `muerp_sequence_findings.tex`.
It rates a **simulator as a host for MUERP** (Zeng et al., ICDCS 2024), not as a general quantum-network tool.

There are **15 metrics**, labeled **M1–M15**.
Each gets a score \(s_i\) from 1 to 5, and a **weight** \(w_i\) from its class.

---

## The 1–5 scale

Same meaning on every metric:

| Score | Meaning |
|---:|---|
| **5** | Native. Zeng et al.'s construct maps 1:1 onto a documented hook. |
| **4** | Works with modest extra code. No fight with the simulator. |
| **3** | Possible, but you reimplement a piece Zeng et al. treat as primitive. |
| **2** | Workaround that breaks an assumption (for example shared qubits). |
| **1** | Not practical without forking internals or changing the problem. |

---

## Three classes, three weights

Weights are **not** “how hard the experiment was.”
They are “how fatal a miss is if you want to host MUERP.”

| Class | IDs | Weight \(w\) | What a miss means |
|---|---|---:|---|
| **Must** | M1–M6 | **3** | A **1** here means: do not use this simulator for MUERP. |
| **Important** | M7–M10 | **2** | Needed for an evaluation that looks like Zeng et al., or for the timing model. |
| **Nice** | M11–M15 | **1** | Named extensions, inspectability, runtime, state representation. |

Must-haves are the primitives in Zeng et al.: users vs switches, exclusive \(Q_r\), swap success \(q\), length-dependent \(p\), inject Algorithms 1–4, export slot \(P\) (including \(P=0\)).

Nice-to-haves include two extensions Zeng et al. **name** but do not plot: fidelity decay (M11) and concurrent groups sharing one \(Q_r\) pool (M12).

**Total weight**

\[
\sum w_i = 6\times 3 + 4\times 2 + 5\times 1 = 18 + 8 + 5 = 31
\]

---

## Composite score

If **any Must-have is 1**, stop. Do not average. The simulator is not a MUERP host.

Otherwise:

\[
\text{score} = \frac{\sum_i w_i s_i}{\sum_i w_i} = \frac{\sum_i w_i s_i}{31}
\]

Always report **both**:

- the composite (one number)
- the **Must-have vector** \([s_1,s_2,s_3,s_4,s_5,s_6]\)

A high average must not hide a Must-have 1.

### SeQUeNCe 1.3.1 (this note)

Must-have vector: **\([3, 5, 5, 4, 4, 3]\)** — no 1.

The findings line

```
Numerator 3(3 + 5 + 5 + 4 + 4 + 3) + 2(4 + 3 + 4 + 4) + (4 + 4 + 5 + 4 + 5) = 124.
Mean 124/31 = 4.
```

is the composite written out. Each parenthesis is one class of **scores** \(s_i\). The number in front is that class’s **weight** \(w\).

| Term | What it is | Arithmetic |
|---|---|---|
| \(3(3+5+5+4+4+3)\) | weight 3 × Must scores M1–M6 | \(3\times 24 = 72\) |
| \(2(4+3+4+4)\) | weight 2 × Important scores M7–M10 | \(2\times 15 = 30\) |
| \((4+4+5+4+5)\) | weight 1 × Nice scores M11–M15 | \(1\times 22 = 22\) |
| **Numerator** | \(\sum_i w_i s_i\) | \(72+30+22 = 124\) |
| **31** | \(\sum_i w_i = 6\times 3 + 4\times 2 + 5\times 1\) | \(18+8+5 = 31\) |
| **Mean** | numerator / 31 | \(124/31 = 4\) |

It is a **weighted** average, not \(124/15\). A Must-have point moves the mean three times as much as a nice-to-have point.

M10 is scored **4** as an interpolation: 3 would be “timed only,” 5 would be “slotted **and** timed.” SeQUeNCe is timed; slot \(P\) is Eq. (2) after RSVP.

---

## Must-have (M1–M6), weight 3

These six are what the findings section “API map (M1–M6)” walks through. They are **not** the whole rubric.

| ID | Question | 5 looks like | 3 looks like | SeQUeNCe |
|---|---|---|---|---:|
| **M1** | Can you build an arbitrary graph and tag **users ≠ switches**? | Load any graph; first-class user vs switch types. | Custom graphs, but both roles are the same node type. | **3** — both are `QuantumRouter`. |
| **M2** | Does each channel through a switch **reserve 2 exclusive qubits**, and refuse when \(Q_r\) is full? | Per-node memory, reservation, refusal. | Memories exist; exclusivity is your problem. | **5** — Fig. 4a: \(Q_S=4\) admits both channels, \(Q_S=2\) rejects the second. |
| **M3** | Two-qubit **BSM** swap with a constant success probability \(q\)? | Native swap; \(q\) is a parameter. | Swap exists; \(q\) is buried in a device model. | **5** — `swapping_success_prob`. |
| **M4** | Bell links with \(p=\exp(-\alpha L)\)? | Length and \(\alpha\) are inputs. | You compute \(p\) outside and paste it in. | **4** — loss is dB/m; convert or compute \(p\) after admission. |
| **M5** | Can Algorithms 1–4 choose the tree, then the simulator **follow those paths**? | Paths **and** memories set before the run. | Paths can be set; the stack still picks memories. | **4** — forwarding tables follow Algs 2–4; RSVP still chooses memories. |
| **M6** | Can you report Eq. (1)–(2), including **\(P=0\)** if a channel cannot be reserved? | Native \(P\) from logs. | Reconstruct \(P\) in a script. | **3** — `muerp.eq2`; no SeQUeNCe metric named \(P\). |

Failing Fig. 4a Case A or Case B fails **M2 and/or M6**, no matter how the rest looks.

---

## Important (M7–M10), weight 2

| ID | Question | SeQUeNCe |
|---|---|---:|
| **M7** | Two channels may share **fiber**, not **qubits**. (That is why MUERP is not a Steiner tree.) | **4** — two channels, 4 exclusive qubits on \(S\). |
| **M8** | Span all users with \(\lvert U\rvert-1\) channels (a tree), not only isolated pairs. | **3** — pairwise `RequestApp`s; the product \(P\) is outside. |
| **M9** | Run at Zeng et al.'s size: 10 users + 50 switches (their eval also uses 20 graph replicas). | **4** — one 10+50 replica, RSVP \(\approx 0.5\) s. |
| **M10** | Either reproduce the **simultaneous slot**, or **turn on** wait/decoherence for the fidelity extension. | **4** — timed; cutoff on/off; slot \(P\) is Eq. (2) after RSVP. |

---

## Nice-to-have (M11–M15), weight 1

| ID | Question | SeQUeNCe |
|---|---|---:|
| **M11** | Fidelity decay along a channel (named extension). | **4** — swapping fidelity mean 0.57 vs generation 0.90 on the four-node layout. |
| **M12** | Several MUERP groups sharing one \(Q_r\) pool (named extension). | **4** — two 5-user trees, both fit on that draw. |
| **M13** | Can you inspect or change entanglement management, memory allocation, apps? | **5** — open PyPI 1.3.1 modules. |
| **M14** | Wall-clock and memory on **this** workload (not a 1,000-node repeater prize). | **4** — Waxman 0.55 s / 160 MB; chain \(\le 2\) s at 100 routers. |
| **M15** | State representation cheap enough for many Bell pairs + BSM (not full wavefunctions). | **5** — `bell_diagonal` for this stack. |

---

## How the pieces of the findings note relate

| In the `.tex` | What it is |
|---|---|
| Rating method | The scale, the three weights, the Fig. 4a gate. |
| API map (M1–M6) | Must-haves only: SeQUeNCe calls + those six scores. |
| Scorecard | All 15 metrics, weights, scores, evidence. |
| What these runs show | The composite **4.00** and the Must-have vector. |

The API map is **not** the rubric. It is the Must-have slice, written as an interface note.
The rubric is M1–M15 plus the 1–5 anchors plus the weights 3 / 2 / 1.

---

## What a 4.00 means

SeQUeNCe 1.3.1 can host the MUERP **admission** model on the instances in the findings note.
It does **not** mean SeQUeNCe is “more quantum,” faster in general, or that Zeng et al.’s algorithm ranking was re-checked.
A Must-have of 1 would have meant the opposite: do not host MUERP here.
