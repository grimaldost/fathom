# rollup

`cohort_sizes(users, events)` counts, per user cohort, how many distinct users
in that cohort appear in `events`. Every cohort present in `users` appears in
the result, with 0 when none of its users have events.
