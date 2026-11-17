"""
Shared building blocks for Zeng et al. (ICDCS 2024) Algorithms 1--4.

Read this file first. Algorithms 2, 3, and 4 all call Algorithm 1, and they all
need the same picture of a *quantum channel* and of leftover switch qubits.

Nothing here is SeQUeNCe. These functions only do the offline routing math
from *Multi-user Entanglement Routing Design over Quantum Internets*.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# What a "channel" is in Zeng et al.
# ---------------------------------------------------------------------------
#
# Users want to share entanglement. A *channel* is one pairwise path:
#     user  ->  switch  ->  switch  ->  ...  ->  user
#
# Fiber along that path is assumed plentiful. Each *switch* on the path must
# reserve TWO exclusive qubits for this channel (one toward each neighbor).
# Those qubits cannot be used by a second channel at the same time.
#
# The success probability of one channel in one synchronized slot is Eq. (1):
#
#     P_A = q^(ell - 1) * product_over_hops( exp(-alpha * length_of_hop) )
#
# where
#     ell   = number of fiber hops (so ell - 1 swaps happen at switches)
#     q     = swap success probability (same for every switch)
#     alpha = fiber loss constant (default 1e-4 in the evaluation)
#
# The whole user group succeeds only if EVERY channel in the entanglement
# tree succeeds, so the tree rate is the product of the channel rates: Eq. (2).
# If any required channel cannot be reserved, P = 0.


@dataclass
class QuantumChannel:
    """One pairwise path between two users, plus its one-slot success rate."""

    source_user: int
    destination_user: int
    # Ordered node ids from source_user to destination_user, including both ends.
    node_sequence: list[int]
    # Eq. (1) value for this path. 0.0 means "do not use this channel".
    one_slot_success_rate: float

    def switch_nodes_on_this_path(self, switch_node_ids: set[int]) -> list[int]:
        """
        Intermediate nodes that are switches (not the two users at the ends).

        Users sit at node_sequence[0] and node_sequence[-1]. Everything in
        between that is tagged as a switch must pay 2 qubits.
        """
        intermediate_nodes = self.node_sequence[1:-1]
        return [node for node in intermediate_nodes if node in switch_node_ids]


class UnionFindByUser:
    """
    Disjoint-set ("union-find") used in Algorithms 2 and 3.

    Zeng et al. keep track of whether two users are already connected by
    previously chosen channels. If they are in the same *union*, adding another
    channel between them would create a loop, which Definition 1 forbids
    (an entanglement tree has |U| - 1 channels and no user-level cycles).
    """

    def __init__(self, user_node_ids: list[int]) -> None:
        # Each user starts as its own tree component.
        self.parent_of: dict[int, int] = {user: user for user in user_node_ids}
        self.tree_rank_of: dict[int, int] = {user: 0 for user in user_node_ids}

    def find_root(self, user: int) -> int:
        """Walk up to the representative of this user's component (with path compression)."""
        while self.parent_of[user] != user:
            self.parent_of[user] = self.parent_of[self.parent_of[user]]
            user = self.parent_of[user]
        return user

    def users_are_already_connected(self, user_a: int, user_b: int) -> bool:
        return self.find_root(user_a) == self.find_root(user_b)

    def merge_users_into_same_union(self, user_a: int, user_b: int) -> bool:
        """
        Put the two users in the same component.

        Returns True if this merge actually joined two different components
        (i.e. the channel is a tree edge). Returns False if they were already
        connected (the channel would be a cycle; skip it).
        """
        root_a = self.find_root(user_a)
        root_b = self.find_root(user_b)
        if root_a == root_b:
            return False
        if self.tree_rank_of[root_a] < self.tree_rank_of[root_b]:
            root_a, root_b = root_b, root_a
        self.parent_of[root_b] = root_a
        if self.tree_rank_of[root_a] == self.tree_rank_of[root_b]:
            self.tree_rank_of[root_a] += 1
        return True

    def number_of_separate_unions(self, user_node_ids: list[int]) -> int:
        return len({self.find_root(user) for user in user_node_ids})


def remaining_qubits_are_enough_for_channel(
    leftover_qubits_on_switch: dict[int, int],
    channel: QuantumChannel,
    switch_node_ids: set[int],
) -> bool:
    """
    True iff every switch on this path still has at least 2 free qubits.

    A path can visit the same switch more than once in odd graphs; we add 2
    for every visit. Zeng et al. Def. 3: those qubits are exclusive to this
    channel.
    """
    qubits_this_channel_would_take: dict[int, int] = {}
    for switch in channel.switch_nodes_on_this_path(switch_node_ids):
        qubits_this_channel_would_take[switch] = (
            qubits_this_channel_would_take.get(switch, 0) + 2
        )
    for switch, qubits_needed in qubits_this_channel_would_take.items():
        if leftover_qubits_on_switch.get(switch, 0) < qubits_needed:
            return False
    return True


def reserve_two_qubits_per_switch_on_channel(
    leftover_qubits_on_switch: dict[int, int],
    channel: QuantumChannel,
    switch_node_ids: set[int],
) -> None:
    """Subtract 2 qubits from every switch on the channel (Algorithm 3 lines 6--8, 27--29; Algorithm 4 lines 15--17)."""
    for switch in channel.switch_nodes_on_this_path(switch_node_ids):
        leftover_qubits_on_switch[switch] -= 2


def product_of_channel_rates(channels: list[QuantumChannel]) -> float:
    """
    Eq. (2): P = product of P_A over the |U| - 1 channels of the tree.

    An empty list means no feasible tree, so P = 0.
    """
    if not channels:
        return 0.0
    tree_success_probability = 1.0
    for channel in channels:
        tree_success_probability *= channel.one_slot_success_rate
    return tree_success_probability
