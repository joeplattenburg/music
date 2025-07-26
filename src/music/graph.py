from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Optional, TypeVar

import numpy as np
from scipy.optimize import linear_sum_assignment

A = TypeVar('A')

@dataclass
class Edge:
    start: Hashable
    end: Hashable
    weight: float


class Graph:
    def __init__(self, nodes: list[Hashable], edges: list[Edge]):
        self.nodes = nodes
        self.edges: dict[tuple[Hashable, Hashable], float] = {}
        self.graph: dict[Hashable, list[Hashable]] = defaultdict(list)
        for edge in edges:
            self.edges[(edge.start, edge.end)] = edge.weight
            self.graph[edge.start].append(edge.end)

    def shortest_path(self, initial: A, terminal: A) -> list[A]:
        costs = {node: float('inf') for node in self.nodes}
        costs[initial] = 0
        predecessors = {}
        unvisited = costs.copy()
        while unvisited:
            unvisited = {node: costs[node] for node in unvisited.keys()}
            current_node = min(unvisited, key=unvisited.get)
            unvisited.pop(current_node)
            neighbors = self.graph[current_node]
            for neighbor in neighbors:
                current_neighbor_cost = costs[neighbor]
                test_neighbor_cost = self.edges[(current_node, neighbor)]
                if test_neighbor_cost < current_neighbor_cost:
                    costs[neighbor] = test_neighbor_cost
                    predecessors[neighbor] = current_node
        # Compute trajectory by backtracking
        current_node = terminal
        trajectory = [terminal]
        while current_node != initial:
            current_node = predecessors[current_node]
            trajectory.append(current_node)
        return list(reversed(trajectory))


def assign(cost_matrix: np.ndarray, assign_surplus: bool = True) -> list[Optional[int]]:
    """
    Solve the assignment problem given an input cost_matrix of shape (m, n) with m >= n.
    If the cost matrix is not square, the general problem will be solved first
    (the n rows that optimize the problem will be assigned)
    and the surplus rows will then be assigned to their lowest cost column (thus duplicating some column assignments)
    if `assign_surplus` is True, or otherwise will be assigned `None`
    """
    if cost_matrix.shape[0] < cost_matrix.shape[1]:
        raise ValueError('`cost_matrix` cannot have more columns than rows')
    assignments = np.array(linear_sum_assignment(cost_matrix)).transpose()
    surplus = set(range(cost_matrix.shape[0])) - set(assignments[:, 0])
    assignments = assignments.tolist()
    for s in surplus:
        assignments.append([s, cost_matrix[s, :].argmin() if assign_surplus else None])
    return [col for _, col in sorted(assignments)]
