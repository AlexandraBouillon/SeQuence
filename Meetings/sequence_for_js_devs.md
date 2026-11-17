# SeQUeNCe, if you already write JS front ends and back ends

You build apps: a browser client, an API, a database, maybe Redis, maybe nginx. SeQUeNCe is not that. It is a **discrete-event simulator** of a quantum network. But the moving parts map onto things you already ship.

This note uses Zeng et al. MUERP (ICDCS 2024) as the product spec: several users want to share entanglement through switches that only have a few quantum memories.

---

## The one-sentence version

SeQUeNCe is an **event loop** plus a **resource-booking API** plus **device microservices**. You do **not** write Zeng et al.’s routing algorithms inside it. You compute the routes in ordinary Python (like a separate pathfinding service), then you tell SeQUeNCe which next hops to use, and it tries to reserve hardware and run the physics.

Think: **your Dijkstra lives in a worker; Express/nginx only follows the route table you uploaded.**

---

## Mental model

| You already know | In SeQUeNCe | In MUERP |
|---|---|---|
| Node event loop / `setTimeout` | `Timeline` | Simulated time, not wall-clock HTTP |
| nginx / React Router / API gateway | Forwarding tables | Which neighbor a request visits next |
| `POST /reservations` + row lock | RSVP + `MemoryTimeCard` | 2 exclusive qubits per channel at a switch |
| Connection pool / hotel rooms | `memo_size` / `MemoryArray` | \(Q_r\) on a switch |
| Microservice instances | `QuantumRouter` | Users **and** switches are this same class |
| A client hitting an endpoint | `RequestApp` | One pairwise channel (Alice–Bob) |
| Retry with backoff | Service window + `memory_counter` | Throughput, **not** slot \(P\) |
| Analytics job after the request | `muerp.eq2` / a Python script | Eq. (1)–(2) \(P\) |
| Pathfinding worker (OSRM, your own Dijkstra) | Algorithms 1–4 (Python, outside) | Choose the entanglement tree |

---

## 1. The event loop (`Timeline`)

A Node server is idle until a request, a timer, or a socket event fires. SeQUeNCe is the same idea, but the “events” are simulated: a photon arrives, a reservation message hits the next router, a memory expires.

There is **no** “handle this HTTP request and return JSON in one shot” for the whole MUERP tree. Time moves. Things queue.

Zeng et al. pretend the whole tree is attempted in **one slot** (every hop and swap at once). SeQUeNCe does **not**. Attempts are one after another on the timeline. For the MUERP *admission* question (“does the tree fit?”) we stop the timeline **before** the physics window and just look at whether RSVP said yes.

**Analogy:** you have a booking API. To see if the hotel can take two overlapping rooms, you do not wait for checkout day. You look at whether `POST /reservations` returned 200 or 409.

---

## 2. Topology is infra, not the product logic

`generate_config` / `RouterNetTopo` is “turn a graph into running instances.”

- Every node becomes a `QuantumRouter`. There is **no** User class and no Switch class that matches MUERP. `sq.Switch` is optical hardware, like a physical NIC, not “the backend service named Switch.”
- You tag roles the way you tag k8s pods: **name** + **memory size**. Alice/Bob/Carol get a large `memo_size`. Switch \(S\) gets \(Q_S = 4\) or \(2\).
- Mid-link `BSMNode`s are extra boxes SeQUeNCe uses to generate entanglement on a fiber. They are **not** Zeng et al.’s switches.

Fig. 4a in product terms: four identical service instances, one of them is the bottleneck because you gave it only 2 or 4 “seats.”

---

## 3. Routing tables, not a path argument

`RequestApp.start(...)` is closer to

```js
await requestEntanglement({ to: "bob", seats: 1, fromTime, toTime });
```

There is **no** `path: ["alice", "S", "bob"]` in that call. The path is whatever the **forwarding table** says, like nginx `proxy_pass` / a next-hop map:

```
alice → S
S     → bob   (for the Alice–Bob session)
```

Algorithms 1–4 (Python) compute that map. You **overwrite** the tables, then start the apps. If you do not, SeQUeNCe uses its own static routing, which is not MUERP.

**Analogy:** you would never put Google Maps inside Express. You get a polyline from a routing service, write it into the gateway config, then the gateway only forwards packets.

---

## 4. RSVP is the booking service (this is the MUERP core)

MUERP Def. 3: a channel through a switch costs **2 exclusive qubits**. Two channels at once on \(S\) need 4.

RSVP is the lock manager:

- Initiator and responder book `memory_size` seats (usually 1 pair).
- Every **intermediate** books **2×** that.
- `MemoryTimeCard` is the unique constraint: overlapping intervals on the same memory → insert fails → `REJECT` (your 409 Conflict).

Fig. 4a:

| \(Q_S\) | What RSVP does | Product language |
|---|---|---|
| 4 | Both Alice–Bob and Alice–Carol get 200 | Two rooms, four beds, both bookings stick |
| 2 | First channel 200, second 409 | Only two beds; second booking refused |

That refusal is the whole “can this tree exist?” test. Algorithms 1–4 do **not** pick which memory indices. RSVP does, the way your ORM picks row ids.

---

## 5. `RequestApp` is a pairwise client, not a multi-user GraphQL mutation

MUERP wants **one tree** of \(|U|-1\) channels. SeQUeNCe only speaks **pair** sessions.

So you open **one app per tree edge**. Fig. 4a: two clients, not one “entangle {alice, bob, carol}” call.

Gotchas that feel like framework bugs:

- Two `start()` calls on the **same** Alice app overwrite `reservation_result` (like mutating one React state twice and only seeing the last write). Read `accepted_reservations` on the switch instead.
- If both channels would use Alice as initiator, reverse the second one (Carol starts toward Alice). Same as “don’t fire two POSTs from the same client identity if the server keys the session on caller.”

---

## 6. Physics is a device layer you can mostly ignore for admission

After RSVP succeeds, the timeline runs entanglement generation (photons on `QuantumChannel`) and swapping (`swapping_success_prob` = Zeng et al.’s \(q\)).

- Loss is **dB/m**, not their \(p = \exp(-\alpha L)\). Convert units, or compute \(p\) yourself after booking. Same idea as storing money in cents and converting for the UI.
- Default \(q\) is **1**, not 0.9. Set it or you silently skip their swap model.
- Mid-link BSM ≠ their \(q\). Wrong service.

For MUERP **admission**, you often **do not run** this layer. Stop before \(t = 1\,\mathrm{s}\). You only needed the 200/409 from RSVP.

---

## 7. Two metrics, like “HTTP 200” vs “requests per second”

| Name | What it answers | Fig. 4a number |
|---|---|---|
| **Slot \(P\)** (Zeng et al.) | If we try the whole tree **once**, what’s the success probability? | \(0.531441\) if both channels booked, else \(0\) |
| **Throughput** (`memory_counter`) | How many pairs landed in a 0.2 s retry window? | e.g. 7 and 10 |

\(P\) is **not** implemented in SeQUeNCe. Multiply \(p\) and \(q\) in a script after you know which channels RSVP accepted. That script is a report job, not the request handler.

If you mix them, you are comparing “probability this checkout succeeds on the first try” to “how many checkouts completed this afternoon.”

---

## 8. Where Algorithms 1–4 sit in the architecture

They are a **pure function** over a graph. No timeline. No HTTP.

```
graph + Q_r + q + alpha
        │
        ▼
  Algorithms 1–4   (Python)
        │
        ▼
  list of paths  +  P_from_formula
        │
        ▼
  write next hops into SeQUeNCe
        │
        ▼
  RSVP  →  200 / 409
        │
        ▼
  optional: run EG/ES for throughput / fidelity
```

- **Alg. 1** — max-rate path for one pair (Dijkstra on \(\alpha L - \ln q\)). Your `shortestPath(from, to)`.
- **Alg. 2** — Kruskal spanning tree, **ignores** small \(Q_r\). Fine when every switch has enough seats for every possible booking.
- **Alg. 3** — Alg. 2’s candidate edges, then drop any booking that would 409, then reconnect leftover components.
- **Alg. 4** — Prim: grow the tree from one user, always attach the best unused user that still fits leftover seats.

SeQUeNCe never calls these. You do, then you **configure** SeQUeNCe.

---

## 9. A “full stack” picture of Fig. 4a

**Spec (product):** Alice, Bob, Carol, switch \(S\). Two channels. Each needs 2 qubits on \(S\). \(p=q=0.9\).

**Pathfinding service:** Alg. 4 (or 3) returns Alice–\(S\)–Bob and Alice–\(S\)–Carol.

**Infra:** four `QuantumRouter`s. `memo_size` on \(S\) is 4 or 2.

**Gateway config:** next hops for those two paths (and the reverse direction).

**Booking API:** two `RequestApp.start`s. \(Q_S=4\) → both 200, \(P=0.531441\). \(Q_S=2\) → one 200, one 409, \(P=0\).

**Optional load test:** let the timeline run 0.2 s and count pairs. That is k6/locust, not the spec’s \(P\).

---

## 10. What you are *not* looking at

- A React UI.
- A REST resource named `/entanglement-tree`.
- A database of qubits. Memories are arrays on each router process, booked in simulated time.
- A built-in MUERP solver. If you do not inject Algorithms 1–4, you are testing SeQUeNCe’s default routing, not Zeng et al.

If you remember one thing: **SeQUeNCe is the runtime and the lock manager. MUERP’s intelligence is a batch job that writes the route table.**

A JS cartoon of this stack (not the real simulator): `Meetings/sequence_js_mockup/`. Run `node src/index.js`.
