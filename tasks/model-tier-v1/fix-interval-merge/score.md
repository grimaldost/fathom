# score — fix-interval-merge

- **author_score:** 45
- **band:** mid
- **predicted tier:** mid / Sonnet (26-55)
- **rationale:** Two independent defects in one merge loop — the touching-boundary
  condition (`start <= last_end + 1`) and the merged end needing `max` rather than the
  latest end. A rushed fix typically handles one and forgets the other, and the shipped
  suite covers neither; getting both right is mid-tier work.
