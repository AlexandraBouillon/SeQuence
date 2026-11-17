"""
Algorithm 1 --- Maximum Entanglement Rate of a Channel
Zeng et al., ICDCS 2024, Section IV-A.

Goal
----
Given two users ui and uj, find ONE path (a *quantum channel*) between them
that maximizes Eq. (1):

    RATE = q^(number_of_hops - 1) * product( exp(-alpha * hop_length) )

That is the probability that every hop succeeds AND every swap along the path
succeeds, in one synchronized slot.

Why not ordinary Dijkstra on length?
------------------------------------
Eq. (1) is a PRODUCT, not a sum. Dijkstra needs additive non-negative weights.
Zeng et al. take logarithms:

    ln(product of t_i) = sum of ln(t_i)

Each factor t_i is in (0, 1], so -ln(t_i) is in [0, +infinity]. Minimizing
the sum of -ln(t_i) is the same as maximizing the product. The edge weight
they use (paper line 12) is:

    alpha * L_uk,uh  -  ln(q)

- alpha * L is -ln(p) because p = exp(-alpha L), so it accounts for fiber loss.
- -ln(q) accounts for one swap associated with traversing that hop.

After Dijkstra finishes, they convert the stored distance back to a rate
(paper line 27):

    RATE = exp( -ln(q) - Dist[uj] )

The extra -ln(q) turns (number_of_hops) factors of q into (number_of_hops - 1),
which matches Eq. (1): you swap once per intermediate switch, not once per hop.

Capacity check while searching (paper line 11)
----------------------------------------------
"for all edges uk--uh with Q_uh >= 2"

If the neighbor uh is a switch that has fewer than 2 qubits left, that hop is
skipped. Users are assumed to have enough memory, so we only apply this test
to nodes in the switch set.

How to run
----------
    python algorithm1_maximum_rate_channel.py
"""

from __future__ import annotations

import math
from typing import Optional

import networkx as nx

from muerp_shared import QuantumChannel


def find_maximum_rate_channel_algorithm1(
    network_graph: nx.Graph,
    source_user: int,
    destination_user: int,
    switch_node_ids: set[int],
    leftover_qubits_on_switch: dict[int, int],
    fiber_loss_constant_alpha: float,
    swap_success_probability_q: float,
) -> Optional[QuantumChannel]:
    """
    Paper Algorithm 1.

    network_graph
        Undirected graph. Every edge must have attribute "length" (same units
        as Zeng et al., default evaluation uses 10k x 10k area with alpha=1e-4).
    leftover_qubits_on_switch
        Remaining Q_r for each switch *right now*. Algorithm 1 itself does not
        subtract qubits; Algorithms 3 and 4 do that after they accept a channel.
    """
    # Paper line 1: no channel yet, RATE starts at 0.
    if source_user == destination_user:
        return None

    # Paper lines 2--3: Dist[uk] = infinity except Dist[ui] = 0.
    # Dist is the transformed "shortest path" cost, NOT the rate itself.
    distance_from_source: dict[int, float] = {
        node: math.inf for node in network_graph.nodes
    }
    distance_from_source[source_user] = 0.0

    # Paper lines 21--26 will walk this map backwards from uj to ui.
    previous_node_on_best_path: dict[int, int] = {}

    # Paper line 4: Visit[uk] = 0 for every node (unvisited).
    node_has_been_settled: dict[int, bool] = {
        node: False for node in network_graph.nodes
    }

    # -ln(q) is a constant added to every hop (paper line 12).
    minus_natural_log_of_q = -math.log(swap_success_probability_q)

    # Paper lines 5--17: classic Dijkstra loop.
    # "while there exists an unvisited uk" then "select uk with minimum Dist".
    while True:
        # Paper line 6: pick the unsettled node with the smallest Dist.
        current_node: Optional[int] = None
        smallest_distance = math.inf
        for node, distance in distance_from_source.items():
            if node_has_been_settled[node]:
                continue
            if distance < smallest_distance:
                smallest_distance = distance
                current_node = node

        # Paper lines 7--8: if the best leftover node is still unreachable, stop.
        if current_node is None or math.isinf(smallest_distance):
            break

        # Paper line 10: mark uk visited.
        node_has_been_settled[current_node] = True

        # We can stop early once uj is settled; its Dist can no longer improve.
        if current_node == destination_user:
            break

        # Paper lines 11--16: relax every neighbor uh with enough qubits.
        for neighbor in network_graph.neighbors(current_node):
            neighbor_is_a_switch = neighbor in switch_node_ids
            neighbor_lacks_two_qubits = (
                leftover_qubits_on_switch.get(neighbor, 0) < 2
            )
            if neighbor_is_a_switch and neighbor_lacks_two_qubits:
                # Paper line 11 condition Q_uh >= 2 failed.
                continue

            hop_length = network_graph[current_node][neighbor]["length"]
            # Paper line 12: Dist[uh] ? Dist[uk] + alpha*L - ln(q)
            additive_edge_weight = (
                fiber_loss_constant_alpha * hop_length + minus_natural_log_of_q
            )
            candidate_distance = smallest_distance + additive_edge_weight

            if candidate_distance < distance_from_source[neighbor]:
                # Paper lines 13--14: this hop improves the path to uh.
                distance_from_source[neighbor] = candidate_distance
                previous_node_on_best_path[neighbor] = current_node

    # Paper lines 18--19: if uj was never reached, there is no valid channel.
    if destination_user not in previous_node_on_best_path:
        return None

    # Paper lines 21--26: reconstruct A_ui,uj by walking Prev from uj back to ui.
    node_sequence_reversed = [destination_user]
    walk_position = destination_user
    while walk_position != source_user:
        walk_position = previous_node_on_best_path[walk_position]
        node_sequence_reversed.append(walk_position)
    node_sequence = list(reversed(node_sequence_reversed))

    # Paper line 27: RATE = exp(-ln q - Dist[uj]).
    distance_at_destination = distance_from_source[destination_user]
    one_slot_success_rate = math.exp(
        -math.log(swap_success_probability_q) - distance_at_destination
    )
    if one_slot_success_rate <= 0.0:
        return None

    return QuantumChannel(
        source_user=source_user,
        destination_user=destination_user,
        node_sequence=node_sequence,
        one_slot_success_rate=one_slot_success_rate,
    )


def _four_node_layout_from_figure_4a() -> tuple[nx.Graph, set[int]]:
    """
    Zeng et al. Fig. 4a device graph: switch 0 in the middle, users 1, 2, 3.

    Lengths are chosen so exp(-alpha * L) = 0.9 when alpha = 1e-4, matching
    the p = 0.9 numbers used in the findings note.
    """
    graph = nx.Graph()
    hop_length_for_p_equals_0_9 = -math.log(0.9) / 1e-4
    for user in (1, 2, 3):
        graph.add_edge(0, user, length=hop_length_for_p_equals_0_9)
    switch_node_ids = {0}
    return graph, switch_node_ids


if __name__ == "__main__":
    graph, switches = _four_node_layout_from_figure_4a()

    # Case A of Fig. 4a: the switch has 4 qubits, so a single channel (2 qubits)
    # is allowed through it.
    leftover = {0: 4}
    alice_to_bob = find_maximum_rate_channel_algorithm1(
        network_graph=graph,
        source_user=1,
        destination_user=2,
        switch_node_ids=switches,
        leftover_qubits_on_switch=leftover,
        fiber_loss_constant_alpha=1e-4,
        swap_success_probability_q=0.9,
    )
    print("Alice--Bob channel:", alice_to_bob)
    if alice_to_bob is not None:
        # One length-2 channel: p * p * q = 0.9^3 = 0.729
        print("Expected RATE for one length-2 channel at p=q=0.9: 0.729")
        print("Computed RATE:", alice_to_bob.one_slot_success_rate)
