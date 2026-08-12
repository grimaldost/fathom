# feedcache

Three cached read views over one tenant's feed: `api.summary`, `report.daily_report`
and `trend.trend`. Each takes the `Store`, a tenant id, the day it is being asked
about as an ISO date string, and that day's data.

## The freshness contract

A cached view is correct when the value it returns is the value that would have been
computed from the arguments it was called with. Two calls that differ in tenant, or
in day, are two different questions and must get two different answers. The `Store`
never expires anything: scope belongs in the key.

`feedcache/keys.py` builds the keys. `feedcache/store.py` is a plain dict and is not
expected to change.
