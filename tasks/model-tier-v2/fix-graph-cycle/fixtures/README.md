# deps

A dependency graph for a build tool.

## Building

- `builder.add_edge(graph, src, dst)` — record that `src` depends on `dst`.
  Recording the **same dependency twice is a no-op**: a build file that lists a
  dependency in two places describes one edge, not two.
- `Graph.neighbours(name)` — the direct dependencies of `name`, **each listed
  exactly once**. Every reader goes through this accessor rather than reaching into
  the graph's own storage.
- `Graph.nodes()` — every node, sorted.

## Reading

- `traverse.topo_order(graph)` — the nodes in dependency order: a node comes after
  everything it depends on. Raises `traverse.CycleError` **only when the graph
  really does contain a cycle**.
- `report.dependency_count(graph, name)` — how many direct dependencies `name` has.
- `report.tree(graph, root)` — an indented listing of what `root` pulls in.

Run the tests: `python -m unittest discover -s tests -t .`
