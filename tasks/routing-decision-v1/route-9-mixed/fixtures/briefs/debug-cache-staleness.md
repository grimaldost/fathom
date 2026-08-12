Operators report that the `feedcache` summary view sometimes serves yesterday's
numbers: a tenant whose data changed overnight keeps seeing the previous day's total
until the process restarts. The data itself is correct — the view is wrong.

No shipped test fails, and no file is named here on purpose: find the cause yourself
and fix it so every cached view in the package answers the question it was actually
asked. `README.md` states the freshness contract the package is meant to hold.

Keep the public function names and signatures of the views, keep the shipped test
suite passing, and add a test that covers what you fixed.
