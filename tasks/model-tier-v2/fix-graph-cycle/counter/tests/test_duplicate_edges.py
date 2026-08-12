import unittest

from deps.builder import Graph, add_edge
from deps.traverse import topo_order


class TestDuplicateEdges(unittest.TestCase):
    def test_a_repeated_dependency_does_not_look_like_a_cycle(self):
        graph = Graph()
        add_edge(graph, "app", "lib")
        add_edge(graph, "app", "lib")
        add_edge(graph, "lib", "core")
        self.assertEqual(topo_order(graph), ["core", "lib", "app"])


if __name__ == "__main__":
    unittest.main()
