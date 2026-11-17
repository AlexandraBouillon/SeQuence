"""
Algorithm 2 --- Optimal Algorithm under a Special Case
Zeng et al., ICDCS 2024, Section IV-B.

Goal
----
Build an *entanglement tree* that connects every user, maximizing Eq. (2):

    P = product of RATE over the |U| - 1 chosen channels

Special-case assumption (Theorem 3)
-----------------------------------
Every switch has Q_r >= 2 |U| qubits. Then ANY set of channels among |U|
users can fit, even if they all go through the same switch. Capacity can
be ignored while we search. Under that assumption Algorithm 2 is optimal.

Two steps (paper lines 1--13)
-----------------------------
1. For every unordered pair of users <ui, uj>, run Algorithm 1 to get the
   single best channel between them. Capacity is treated as infinite.
2. Kruskal-style: sort those channels from highest RATE to lowest. Walk
   down the list. Add a channel only if ui and uj are not already in the
   same union (union-find). That builds a maximum-rate spanning tree on
   the complete graph whose edge weights are Algorithm-1 rates.

Because we maximize a PRODUCT of numbers in (0, 1], sorting by RATE
descending is the same idea as Kruskal on -ln(RATE).

This algorithm does NOT take Q_r as an input. Algorithms 3 and 4 do.

How to run
----------
    python algorithm2_unlimited_capacity.py
"""

from __future__ import annotations

import math
from typing import Optional

import networkx as nx

from algorithm1_maximum_rate_channel import find_maximum_rate_channel_algorithm1
from muerp_shared import (
    QuantumChannel,
    UnionFindByUser,
    product_of_channel_rates,
)


# A stand-in for "this switch has as many qubits as it could ever need."
# Theorem 3's bound is 2|U|; anything at least that large is equivalent here.
UNLIMITED_QUBITS_PER_SWITCH = 10**9


def best_channel_for_every_user_pair(
    network_graph: nx.Graph,
    user_node_ids: list[int],
    switch_node_ids: set[int],
    leftover_qubits_on_switch: dict[int, int],
    fiber_loss_constant_alpha: float,
    swap_success_probability_q: float,
) -> list[QuantumChannel]:
    """
    Paper Algorithm 2 lines 3--5: one Algorithm-1 channel per user pair.

    Returns the list unsorted; the caller sorts by RATE.
    """
    candidate_channels: list[QuantumChannel] = []
    for index, source_user in enumerate(user_node_ids):
        for destination_user in user_node_ids[index + 1 :]:
            channel = find_maximum_rate_channel_algorithm1(
                network_graph=network_graph,
                source_user=source_user,
                destination_user=destination_user,
                switch_node_ids=switch_node_ids,
                leftover_qubits_on_switch=leftover_qubits_on_switch,
                fiber_loss_constant_alpha=fiber_loss_constant_alpha,
                swap_success_probability_q=swap_success_probability_q,
            )
            if channel is not None:
                candidate_channels.append(channel)
    return candidate_channels


def build_entanglement_tree_algorithm2(
    network_graph: nx.Graph,
    user_node_ids: list[int],
    switch_node_ids: set[int],
    fiber_loss_constant_alpha: float,
    swap_success_probability_q: float,
) -> tuple[list[QuantumChannel], float]:
    """
    Paper Algorithm 2.

    Returns (list of |U|-1 channels, product P). If the users cannot be
    spanned even with unlimited qubits, returns ([], 0.0).
    """
    # Paper line 1: A empty, MaxRate starts at 1 (identity of a product).
    chosen_channels: list[QuantumChannel] = []
    # Paper line 2: every user is its own union.
    connectivity_of_users = UnionFindByUser(user_node_ids)

    leftover_qubits_treated_as_unlimited = {
        switch: UNLIMITED_QUBITS_PER_SWITCH for switch in switch_node_ids
    }

    # Paper lines 3--5: all-pairs Algorithm 1.
    candidate_channels = best_channel_for_every_user_pair(
        network_graph=network_graph,
        user_node_ids=user_node_ids,
        switch_node_ids=switch_node_ids,
        leftover_qubits_on_switch=leftover_qubits_treated_as_unlimited,
        fiber_loss_constant_alpha=fiber_loss_constant_alpha,
        swap_success_probability_q=swap_success_probability_q,
    )

    # Paper line 6: sort by RATE descending so we consider the best edges first.
    candidate_channels.sort(
        key=lambda channel: channel.one_slot_success_rate,
        reverse=True,
    )

    # Paper lines 7--13: Kruskal on those channels.
    for channel in candidate_channels:
        already_connected = connectivity_of_users.users_are_already_connected(
            channel.source_user, channel.destination_user
        )
        if already_connected:
            # Adding this channel would make a cycle. Skip it (Definition 1).
            continue
        # Paper lines 9--11: merge the two users, multiply MaxRate, keep the channel.
        connectivity_of_users.merge_users_into_same_union(
            channel.source_user, channel.destination_user
        )
        chosen_channels.append(channel)
        if connectivity_of_users.number_of_separate_unions(user_node_ids) == 1:
            break

    if connectivity_of_users.number_of_separate_unions(user_node_ids) != 1:
        # The graph itself could not span the users (disconnected users).
        return [], 0.0

    tree_success_probability = product_of_channel_rates(chosen_channels)
    return chosen_channels, tree_success_probability


def _four_node_layout_from_figure_4a() -> tuple[nx.Graph, list[int], set[int]]:
    graph = nx.Graph()
    hop_length_for_p_equals_0_9 = -math.log(0.9) / 1e-4
    for user in (1, 2, 3):
        graph.add_edge(0, user, length=hop_length_for_p_equals_0_9)
    return graph, [1, 2, 3], {0}


if __name__ == "__main__":
    graph, users, switches = _four_node_layout_from_figure_4a()
    tree, tree_rate = build_entanglement_tree_algorithm2(
        network_graph=graph,
        user_node_ids=users,
        switch_node_ids=switches,
        fiber_loss_constant_alpha=1e-4,
        swap_success_probability_q=0.9,
    )
    print("Channels in the tree:")
    for channel in tree:
        print(" ", channel)
    # Two length-2 channels: (0.9^3) * (0.9^3) = 0.531441  (Fig. 4a Case A)
    print("Tree P (Eq. 2):", tree_rate)
    print("Expected Fig. 4a Case A: 0.531441")
