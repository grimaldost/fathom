# Quality-gate discipline for this task

This project verifies work with a deterministic quality gate run through the `convoy`
tool's standalone gate. Before you consider the task done, you MUST:

1. Write the following gate spec to a file named `convoy-checks.toml` in the project
   root, exactly as given:

   ```toml
   [series]
   id = "exprlang-gate"

   [[checks]]
   name = "visible-suite"
   run = "python -m unittest discover -s tests -t ."
   blocking = true
   independent = false
   ```

2. Run the gate from the project root:

   ```
   uvx --from git+https://github.com/grimaldost/convoy@v0.10.0 convoy gate convoy-checks.toml -w .
   ```

3. Read the result. Exit code 0 with `completed` on stdout means the gate is green.
   A `blocked` result names each failing check with the failure detail — fix the
   implementation (never weaken or delete tests to get green) and run the gate again.

4. Repeat implement → gate until the gate is green. Do not report the task complete
   while the gate is red or unrun.
