"""
Algorithm 3 --- Conflict-free Algorithm
Zeng et al., ICDCS 2024, Section IV-C.

Goal
----
Same as Algorithm 2 (an entanglement tree maximizing Eq. (2)), but now each
switch only has a *finite* qubit budget Q_r. Two qubits are exclusive to each
channel that passes through a switch. If a switch would overflow, that channel
is refused and the users must be connected some other way.

Why Algorithm 2 is not enough
-----------------------------
Algorithm 2 pretends Q_r >= 2|U|, so it never checks leftover qubits. On the
Fig. 4a layout with Q_S = 2, Algorithm 2 would still return two channels and
P = 0.531, which is physically infeasible. Algorithm 3 is the greedy repair.

Input A (paper: "Input: G, Q, A")
---------------------------------
A is the set of all-pair Algorithm-1 channels from Algorithm 2's first step
(unlimited capacity). We sort that set by RATE and try to keep the best
channels that still fit in leftover Q_r.

Two phases (paper lines 3--33)
------------------------------
Phase 1 (lines 3--15). Walk channels from best RATE to worst. If every switch
on the path still has at least 2 qubits, reserve them, merge the two users,
keep the channel. If not, skip it (those two users stay in different unions).

Phase 2 (lines 16--33). While some users are still in different unions, run
Algorithm 1 between every pair of users in different unions, using the
*remaining* Q_r. Keep the single highest-RATE feasible channel, reserve its
qubits, merge. If no such channel exists, terminate: no feasible tree, P = 0.

Greedy rule (paper text after the listing)
------------------------------------------
Always keep / reconnect with the channel of maximum RATE. That is the only
tie-break.

How to run
----------
    python algorithm3_conflict_free.py
"""

from __future__ import annotations

import math
from typing import Optional

import networkx as nx

from algorithm1_maximum_rate_channel import find_maximum_rate_channel_algorithm1
from algorithm2_unlimited_capacity import (
    UNLIMITED_QUBITS_PER_SWITCH,
    best_channel_for_every_user_pair,
)
from muerp_shared import (
    QuantumChannel,
    UnionFindByUser,
    product_of_channel_rates,
    remaining_qubits_are_enough_for_channel,
    reserve_two_qubits_per_switch_on_channel,
)


def _reconnect_separate_unions_until_one_tree(
    network_graph: nx.Graph,
    user_node_ids: list[int],
    switch_node_ids: set[int],
    leftover_qubits_on_switch: dict[int, int],
    connectivity_of_users: UnionFindByUser,
    fiber_loss_constant_alpha: float,
    swap_success_probability_q: float,
    chosen_channels: list[QuantumChannel],
) -> bool:
    """
    Paper Algorithm 3 lines 16--33.

    Returns True if every user ends in one union. Returns False if we cannot
    find a feasible reconnecting channel (paper lines 24--25).
    """
    while connectivity_of_users.number_of_separate_unions(user_node_ids) > 1:
        # Paper line 17: CurrentRate <- 0
        best_reconnecting_channel: Optional[QuantumChannel] = None

        # Paper lines 18--23: try every pair of users in different unions.
        for index, user_a in enumerate(user_node_ids):
            for user_b in user_node_ids[index + 1 :]:
                if connectivity_of_users.users_are_already_connected(user_a, user_b):
                    continue
                candidate = find_maximum_rate_channel_algorithm1(
                    network_graph=network_graph,
                    source_user=user_a,
                    destination_user=user_b,
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
                    best_reconnecting_channel is None
                    or candidate.one_slot_success_rate
                    > best_reconnecting_channel.one_slot_success_rate
                ):
                    best_reconnecting_channel = candidate

        # Paper lines 24--25: CurrentRate = 0 means no feasible reconnect.
        if best_reconnecting_channel is None:
            return False

        # Paper lines 27--32: spend 2 qubits per switch, merge, keep the channel.
        reserve_two_qubits_per_switch_on_channel(
            leftover_qubits_on_switch,
            best_reconnecting_channel,
            switch_node_ids,
        )
        connectivity_of_users.merge_users_into_same_union(
            best_reconnecting_channel.source_user,
            best_reconnecting_channel.destination_user,
        )
        chosen_channels.append(best_reconnecting_channel)

    return True


def build_entanglement_tree_algorithm3(
    network_graph: nx.Graph,
    user_node_ids: list[int],
    switch_node_ids: set[int],
    qubits_per_switch: int,
    fiber_loss_constant_alpha: float,
    swap_success_probability_q: float,
) -> tuple[list[QuantumChannel], float]:
    """
    Paper Algorithm 3.

    qubits_per_switch is Q_r, the same budget on every switch (Zeng et al.
    default is 4). Returns ([], 0.0) when no conflict-free tree exists.
    """
    # Paper line 1: A' empty, MaxRate starts at 1.
    chosen_channels: list[QuantumChannel] = []
    # Paper line 2: every user starts in its own union.
    connectivity_of_users = UnionFindByUser(user_node_ids)

    leftover_qubits_on_switch = {
        switch: qubits_per_switch for switch in switch_node_ids
    }

    # Input A: all-pair Algorithm-1 channels as if capacity were unlimited
    # (Algorithm 2's first step). Finite Q_r is enforced below, not inside
    # this call.
    leftover_qubits_treated_as_unlimited = {
        switch: UNLIMITED_QUBITS_PER_SWITCH for switch in switch_node_ids
    }
    candidate_channels = best_channel_for_every_user_pair(
        network_graph=network_graph,
        user_node_ids=user_node_ids,
        switch_node_ids=switch_node_ids,
        leftover_qubits_on_switch=leftover_qubits_treated_as_unlimited,
        fiber_loss_constant_alpha=fiber_loss_constant_alpha,
        swap_success_probability_q=swap_success_probability_q,
    )

    # Paper line 3: sort A by RATE descending.
    candidate_channels.sort(
        key=lambda channel: channel.one_slot_success_rate,
        reverse=True,
    )

    # Paper lines 4--15: keep a channel only if every switch on it still has Q >= 2.
    for channel in candidate_channels:
        path_fits = remaining_qubits_are_enough_for_channel(
            leftover_qubits_on_switch, channel, switch_node_ids
        )
        if not path_fits:
            # Paper lines 12--13: do not merge these users.
            continue
        merged = connectivity_of_users.merge_users_into_same_union(
            channel.source_user, channel.destination_user
        )
        if not merged:
            # Already in the same union: this channel would be a cycle.
            continue
        # Paper lines 6--8 and 9--11: subtract 2 qubits per switch, keep channel.
        reserve_two_qubits_per_switch_on_channel(
            leftover_qubits_on_switch, channel, switch_node_ids
        )
        chosen_channels.append(channel)

    # Paper lines 16--33: reconnect whatever unions are still split.
    reconnected = _reconnect_separate_unions_until_one_tree(
        network_graph=network_graph,
        user_node_ids=user_node_ids,
        switch_node_ids=switch_node_ids,
        leftover_qubits_on_switch=leftover_qubits_on_switch,
        connectivity_of_users=connectivity_of_users,
        fiber_loss_constant_alpha=fiber_loss_constant_alpha,
        swap_success_probability_q=swap_success_probability_q,
        chosen_channels=chosen_channels,
    )
    if not reconnected:
        return [], 0.0

    return chosen_channels, product_of_channel_rates(chosen_channels)


def _four_node_layout_from_figure_4a() -> tuple[nx.Graph, list[int], set[int]]:
    graph = nx.Graph()
    hop_length_for_p_equals_0_9 = -math.log(0.9) / 1e-4
    for user in (1, 2, 3):
        graph.add_edge(0, user, length=hop_length_for_p_equals_0_9)
    return graph, [1, 2, 3], {0}


if __name__ == "__main__":
    graph, users, switches = _four_node_layout_from_figure_4a()

    print("--- Fig. 4a Case A: Q_S = 4 (two channels fit) ---")
    tree_a, rate_a = build_entanglement_tree_algorithm3(
        network_graph=graph,
        user_node_ids=users,
        switch_node_ids=switches,
        qubits_per_switch=4,
        fiber_loss_constant_alpha=1e-4,
        swap_success_probability_q=0.9,
    )
    print("channels:", len(tree_a), "P =", rate_a, "(expected 0.531441)")

    print("--- Fig. 4a Case B: Q_S = 2 (second channel cannot be reserved) ---")
    tree_b, rate_b = build_entanglement_tree_algorithm3(
        network_graph=graph,
        user_node_ids=users,
        switch_node_ids=switches,
        qubits_per_switch=2,
        fiber_loss_constant_alpha=1e-4,
        swap_success_probability_q=0.9,
    )
    print("channels:", len(tree_b), "P =", rate_b, "(expected 0)")
