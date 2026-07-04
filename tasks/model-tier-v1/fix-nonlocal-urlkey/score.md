# score — fix-nonlocal-urlkey

- **author_score:** 74
- **band:** high
- **predicted tier:** strong / Opus (56-100)
- **rationale:** A non-local root-cause task. The symptom (pages split by query string /
  trailing slash) surfaces in `page_counts` and `top_page`, but the real defect is the
  shared `page_key` returning the URL raw. A band-aid that canonicalizes inside
  `page_counts` fixes `page_counts_merge` yet leaves `top_page` — a second, independent
  caller of `page_key` — broken; only fixing `page_key` passes both hard criteria.
- **Capability Haiku is expected to LACK:** recognizing that two independent call sites
  share one helper (`page_key`) and that the correct single fix point is that helper, not
  the first call site that happened to show the symptom — canonicalizing URL state
  (strip query string and trailing slash) once at the shared seam rather than per caller.
