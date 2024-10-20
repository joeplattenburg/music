
from music import graph


def test_graph() -> None:
    nodes = {n: graph.Node(n) for n in ['a', 'b', 'c', 'd']}
    edges = [
        graph.Edge(boundaries=(nodes['a'], nodes['b']), weight=2.0),
        graph.Edge(boundaries=(nodes['a'], nodes['c']), weight=1.0),
        graph.Edge(boundaries=(nodes['b'], nodes['d']), weight=1.0),
        graph.Edge(boundaries=(nodes['c'], nodes['d']), weight=1.0),
    ]
    g = graph.Graph(
        nodes=list(nodes.values()),
        edges=edges,
    )
    expected = [nodes['a'], nodes['c'], nodes['d']]
    actual = g.shortest_path(nodes['a'], nodes['d'])
    assert actual == expected
