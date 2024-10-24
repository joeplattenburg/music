from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable


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

    def shortest_path(self, initial: Hashable, terminal: Hashable) -> list[Hashable]:
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


