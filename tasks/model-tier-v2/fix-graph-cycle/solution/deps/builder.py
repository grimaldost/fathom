"""Build a dependency graph."""


class Graph:
    """A dependency graph: each node maps to the nodes it depends on."""

    def __init__(self):
        self._edges = {}

    def add_node(self, name):
        """Register *name*, with no dependencies of its own yet."""
        self._edges.setdefault(name, [])

    def neighbours(self, name):
        """The direct dependencies of *name*, each listed exactly once."""
        return list(self._edges.get(name, []))

    def nodes(self):
        """Every node in the graph, sorted."""
        return sorted(self._edges)


def add_edge(graph, src, dst):
    """Record that *src* depends on *dst*. Recording it twice is a no-op."""
    graph.add_node(src)
    graph.add_node(dst)
    if dst not in graph._edges[src]:
        graph._edges[src].append(dst)
