# ranges

Both bound helpers treat the interval as CLOSED: `lower_bound` returns the
first index whose value is >= the target, `upper_bound` the last index whose
value is <= it. An empty list yields -1 from either.
