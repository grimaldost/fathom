# Package conventions

- Public functions take and return plain builtins and the namedtuples in
  `recon/model.py`. No new record types.
- Ids are compared as strings and ordered ascending; times are integer seconds.
- Counts reported by `recon/report.py` are counts of **readings**, never of devices
  — a device that accounts for a reading contributes one to `matched`, and a device
  that accounts for none contributes nothing to any count.
- Every list a public function returns is ordered deterministically. Input order is
  not an ordering.
