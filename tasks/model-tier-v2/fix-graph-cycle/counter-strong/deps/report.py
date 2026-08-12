"""Report on a dependency graph.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 3 of 3 (harness-side, never staged).
"""


def dependency_count(graph, name):
    """How many direct dependencies *name* has."""
    return len(graph.unique_neighbours(name))


def tree(graph, root, depth=0):
    """An indented listing of everything *root* pulls in."""
    lines = ["  " * depth + root]
    for dep in graph.unique_neighbours(root):
        lines.extend(tree(graph, dep, depth + 1))
    return lines
