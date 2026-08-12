import unittest

from deps.builder import Graph, add_edge
from deps.report import dependency_count, tree
from deps.traverse import topo_order


def doubled():
    graph = Graph()
    add_edge(graph, "app", "lib")
    add_edge(graph, "app", "lib")
    add_edge(graph, "lib", "core")
    return graph


class TestDuplicateEdges(unittest.TestCase):
    def test_a_repeated_dependency_is_recorded_once(self):
        self.assertEqual(doubled().neighbours("app"), ["lib"])

    def test_a_repeated_dependency_does_not_look_like_a_cycle(self):
        self.assertEqual(topo_order(doubled()), ["core", "lib", "app"])

    def test_readers_see_the_dependency_once(self):
        self.assertEqual(dependency_count(doubled(), "app"), 1)
        self.assertEqual(tree(doubled(), "app"), ["app", "  lib", "    core"])


if __name__ == "__main__":
    unittest.main()
