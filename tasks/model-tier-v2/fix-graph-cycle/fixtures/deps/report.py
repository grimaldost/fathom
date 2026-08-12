"""Report on a dependency graph."""


def dependency_count(graph, name):
    """How many direct dependencies *name* has."""
    return len(graph.neighbours(name))


def tree(graph, root, depth=0):
    """An indented listing of everything *root* pulls in."""
    lines = ["  " * depth + root]
    for dep in graph.neighbours(root):
        lines.extend(tree(graph, dep, depth + 1))
    return lines
