
from music import graph


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
