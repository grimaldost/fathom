Users of the `rangekit` package report that `clamp(-5, 0, 10)` comes back as `-5`
instead of `0`. Find and fix the bug so `clamp` behaves as documented in the
package README for every input. Preserve the existing public API, and keep the
shipped test suite passing.
