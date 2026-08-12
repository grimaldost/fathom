# rollup

`histogram(values, edges)` counts values into half-open buckets `[lo, hi)`,
except the LAST bucket which is closed `[lo, hi]` so the maximum edge is
counted. Values outside the edges are not counted.
