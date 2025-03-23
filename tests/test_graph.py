
from music import graph

import numpy as np
import pytest


def test_graph() -> None:
    nodes = ['a', 'b', 'c', 'd']
    edges = [
        graph.Edge(start='a', end='b', weight=2.0),
        graph.Edge(start='a', end='c', weight=1.0),
        graph.Edge(start='b', end='d', weight=1.0),
        graph.Edge(start='c', end='d', weight=1.0),
    ]
    g = graph.Graph(nodes=nodes, edges=edges)
    expected = ['a', 'c', 'd']
    actual = g.shortest_path('a', 'd')
    assert actual == expected


@pytest.mark.parametrize(
    'cost_matrix,expected',
    [
        ([[3, 1, 2], [1, 2, 3], [3, 2, 1]], [1, 0, 2]),
        ([[3, 1, 2], [1, 2, 3], [3, 2, 1], [0, 100, 50]], [1, 0, 2, 0]),
        ([[3, 1, 2], [1, 2, 3], [1, 1, 0], [3, 2, 1], [0, 100, 50]], [1, 0, 2, 2, 0]),
    ]
)
def test_assign(cost_matrix, expected) -> None:
    actual = graph.assign(np.array(cost_matrix))
    assert actual == expected


@pytest.mark.parametrize(
    'cost_matrix,expected',
    [
        ([[3, 1, 2], [1, 2, 3], [3, 2, 1]], [1, 0, 2]),
        ([[3, 1, 2], [1, 2, 3], [3, 2, 1], [0, 100, 50]], [1, None, 2, 0]),
        ([[3, 1, 2], [1, 2, 3], [1, 1, 0], [3, 2, 1], [0, 100, 50]], [1, None, 2, None, 0]),
    ]
)
def test_assign_without_surplus(cost_matrix, expected) -> None:
    actual = graph.assign(np.array(cost_matrix), assign_surplus=False)
    assert actual == expected
