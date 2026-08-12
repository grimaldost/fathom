"""Walk a dependency graph.

COUNTER-SOLUTION FOR THE STRONG ORACLE, part 2 of 3 (harness-side, never staged).
"""


class CycleError(Exception):
    """The graph contains a dependency cycle."""


def topo_order(graph):
    """Nodes in dependency order: a node comes after everything it depends on."""
    dependents = {name: set() for name in graph.nodes()}
    pending = {}
    for name in graph.nodes():
        deps = graph.unique_neighbours(name)
        pending[name] = len(deps)
        for dep in deps:
            dependents[dep].add(name)

    ready = sorted(name for name, count in pending.items() if count == 0)
    order = []
    while ready:
        name = ready.pop(0)
        order.append(name)
        for dependent in sorted(dependents[name]):
            pending[dependent] -= 1
            if pending[dependent] == 0:
                ready.append(dependent)
        ready.sort()

    if len(order) != len(pending):
        raise CycleError("the dependency graph contains a cycle")
    return order
