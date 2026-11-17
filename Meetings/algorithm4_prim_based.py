"""
Algorithm 4 --- Prim-based Algorithm
Zeng et al., ICDCS 2024, Section IV-D.

Goal
----
Build a feasible entanglement tree under finite Q_r, *without* first running
Algorithm 2. Algorithm 3 needs Algorithm 2's all-pair candidate list as input.
Algorithm 4 grows the tree the way Prim's minimum spanning tree grows: start
at one user and always attach the best unused user.

Prim picture
------------
U1 = users already in the tree  (starts as {u0})
U2 = users not yet attached     (starts as U minus {u0})

Repeat |U| - 1 times:
    Look at every pair (ui in U1, uj in U2).
    Run Algorithm 1 for that pair, skipping switches with Q < 2.
    Pick the pair with the largest RATE.
    Move uj from U2 into U1.
    Subtract 2 qubits from every switch on that channel.

If a round finds no feasible channel, terminate: P = 0.

Why this can differ from Algorithm 3
------------------------------------
Algorithm 3 first tries to keep Algorithm 2's globally best edges, then
repairs capacity conflicts. Algorithm 4 never sees the global all-pairs
ranking; it only compares edges that *touch the current tree*. On easy
graphs (lots of leftover Q_r) they often return the same tree. On tight
Q_r they can disagree. Zeng et al. write that at Q_i = 2 only Algorithm 3
supported entanglement in their Fig. 8a plots.

How to run
----------
    python algorithm4_prim_based.py
"""

from __future__ import annotations

import math
from typing import Optional

import networkx as nx

from algorithm1_maximum_rate_channel import find_maximum_rate_channel_algorithm1
from muerp_shared import (
    QuantumChannel,
    product_of_channel_rates,
    remaining_qubits_are_enough_for_channel,
    reserve_two_qubits_per_switch_on_channel,
)


def build_entanglement_tree_algorithm4(
    network_graph: nx.Graph,
    user_node_ids: list[int],
    switch_node_ids: set[int],
    qubits_per_switch: int,
    fiber_loss_constant_alpha: float,
    swap_success_probability_q: float,
    starting_user: Optional[int] = None,
) -> tuple[list[QuantumChannel], float]:
    """
    Paper Algorithm 4.

    starting_user is paper line 2 ("randomly pick u0 in U"). If None, the
    first user in user_node_ids is used so the demo is deterministic.
    """
    # Paper line 1: A'' empty, MaxRate starts at 1.
    chosen_channels: list[QuantumChannel] = []

    leftover_qubits_on_switch = {
        switch: qubits_per_switch for switch in switch_node_ids
    }

    # Paper lines 2--3: U1 = {u0}, U2 = U \ {u0}.
    if starting_user is None:
        starting_user = user_node_ids[0]
    users_already_in_the_tree: set[int] = {starting_user}
    users_not_yet_attached: set[int] = set(user_node_ids) - users_already_in_the_tree

    # Paper line 4: while U2 is not empty  (exactly |U| - 1 successful rounds).
    while users_not_yet_attached:
        # Paper line 5: CurrentRate <- 0
        best_channel_touching_the_tree: Optional[QuantumChannel] = None

        # Paper lines 6--11: every ui in U1, every uj in U2.
        for user_inside_tree in users_already_in_the_tree:
            for user_outside_tree in users_not_yet_attached:
                candidate = find_maximum_rate_channel_algorithm1(
                    network_graph=network_graph,
                    source_user=user_inside_tree,
                    destination_user=user_outside_tree,
                    switch_node_ids=switch_node_ids,
                    leftover_qubits_on_switch=leftover_qubits_on_switch,
                    fiber_loss_constant_alpha=fiber_loss_constant_alpha,
                    swap_success_probability_q=swap_success_probability_q,
                )
                if candidate is None:
                    continue
                if not remaining_qubits_are_enough_for_channel(
                    leftover_qubits_on_switch, candidate, switch_node_ids
                ):
                    continue
                if (
                    best_channel_touching_the_tree is None
                    or candidate.one_slot_success_rate
                    > best_channel_touching_the_tree.one_slot_success_rate
                ):
                    best_channel_touching_the_tree = candidate

        # Paper lines 12--13: no feasible attachment this round.
        if best_channel_touching_the_tree is None:
            return [], 0.0

        # Paper lines 15--17: Q_rk <- Q_rk - 2 on every switch on the channel.
        reserve_two_qubits_per_switch_on_channel(
            leftover_qubits_on_switch,
            best_channel_touching_the_tree,
            switch_node_ids,
        )
        chosen_channels.append(best_channel_touching_the_tree)

        # Paper line 19: U1 <- U1 + u2, U2 <- U2 - u2.
        # u2 is whichever endpoint was still outside the tree.
        newly_attached_user = best_channel_touching_the_tree.destination_user
        if newly_attached_user not in users_not_yet_attached:
            newly_attached_user = best_channel_touching_the_tree.source_user
        users_already_in_the_tree.add(newly_attached_user)
        users_not_yet_attached.remove(newly_attached_user)

    return chosen_channels, product_of_channel_rates(chosen_channels)


def _four_node_layout_from_figure_4a() -> tuple[nx.Graph, list[int], set[int]]:
    graph = nx.Graph()
    hop_length_for_p_equals_0_9 = -math.log(0.9) / 1e-4
    for user in (1, 2, 3):
        graph.add_edge(0, user, length=hop_length_for_p_equals_0_9)
    return graph, [1, 2, 3], {0}


if __name__ == "__main__":
    graph, users, switches = _four_node_layout_from_figure_4a()

    print("--- Fig. 4a Case A: Q_S = 4 ---")
    tree_a, rate_a = build_entanglement_tree_algorithm4(
        network_graph=graph,
        user_node_ids=users,
        switch_node_ids=switches,
        qubits_per_switch=4,
        fiber_loss_constant_alpha=1e-4,
        swap_success_probability_q=0.9,
        starting_user=1,
    )
    print("channels:", len(tree_a), "P =", rate_a, "(expected 0.531441)")
    for channel in tree_a:
        print(" ", channel.node_sequence, "RATE", channel.one_slot_success_rate)

    print("--- Fig. 4a Case B: Q_S = 2 (Alg. 4 should return no tree) ---")
    tree_b, rate_b = build_entanglement_tree_algorithm4(
        network_graph=graph,
        user_node_ids=users,
        switch_node_ids=switches,
        qubits_per_switch=2,
        fiber_loss_constant_alpha=1e-4,
        swap_success_probability_q=0.9,
        starting_user=1,
    )
    print("channels:", len(tree_b), "P =", rate_b, "(expected 0)")
