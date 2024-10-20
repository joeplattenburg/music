from collections import defaultdict
from typing import Hashable, Optional, Literal


class Node:
    def __init__(self, name: Hashable):
        self.name = name

    def __repr__(self):
        return str(self.name)

    def __str__(self):
        return str(self.name)


class Edge:
    def __init__(self, boundaries: tuple[Node, Node], weight: Optional[float]):
        self.boundaries = boundaries
        self.weight = weight


class Graph:
    def __init__(self, nodes: list[Node], edges: list[Edge]):
        self.nodes = nodes
        self.edges: dict[tuple[Node, Node], float] = {}
        self.graph: dict[Node, list[Node]] = defaultdict(list)
        for edge in edges:
            self.edges[edge.boundaries] = edge.weight
            self.graph[edge.boundaries[0]].append(edge.boundaries[1])

    def shortest_path(self, initial: Node, terminal: Node) -> list[Node]:
        costs: dict[Node: float] = {node: float('inf') for node in self.nodes}
        costs[initial] = 0
        predecessors: dict[Node, Node] = {}
        unvisited = costs.copy()
        while unvisited:
            unvisited = {node: costs[node] for node in unvisited.keys()}
            current_node = min(unvisited, key=unvisited.get)
            unvisited.pop(current_node)
            neighbors = self.graph[current_node]
            print(current_node, len(unvisited), len(neighbors))
            for neighbor in neighbors:
                current_neighbor_cost = costs[neighbor]
                test_neighbor_cost = self.edges[(current_node, neighbor)]
                if test_neighbor_cost < current_neighbor_cost:
                    costs[neighbor] = test_neighbor_cost
                    predecessors[neighbor] = current_node
        # Compute trajectory by backtracking
        current_node = terminal
        trajectory: list[Node] = [terminal]
        while current_node != initial:
            current_node = predecessors[current_node]
            trajectory.append(current_node)
        return list(reversed(trajectory))


