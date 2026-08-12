import unittest

from deps.builder import Graph, add_edge
from deps.report import dependency_count, tree
from deps.traverse import CycleError, topo_order


def graph_of(*edges):
    graph = Graph()
    for src, dst in edges:
        add_edge(graph, src, dst)
    return graph


class TestGraph(unittest.TestCase):
    def test_topo_order_puts_dependencies_first(self):
        graph = graph_of(("app", "lib"), ("lib", "core"))
        self.assertEqual(topo_order(graph), ["core", "lib", "app"])

    def test_dependency_count(self):
        graph = graph_of(("app", "lib"), ("app", "core"))
        self.assertEqual(dependency_count(graph, "app"), 2)
        self.assertEqual(dependency_count(graph, "lib"), 0)

    def test_tree_indents_each_level(self):
        graph = graph_of(("app", "lib"), ("lib", "core"))
        self.assertEqual(tree(graph, "app"), ["app", "  lib", "    core"])

    def test_a_real_cycle_is_reported(self):
        graph = graph_of(("a", "b"), ("b", "a"))
        with self.assertRaises(CycleError):
            topo_order(graph)


if __name__ == "__main__":
    unittest.main()
