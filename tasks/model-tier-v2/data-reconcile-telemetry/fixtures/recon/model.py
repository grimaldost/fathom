"""The two records this package reconciles. Not an edit site."""

from collections import namedtuple

# A telemetry reading: `at` is integer seconds, `id` is the reading id.
Reading = namedtuple("Reading", "id at value")

# A registered device: `seen_at` is integer seconds, `tolerance` is in seconds.
Device = namedtuple("Device", "id seen_at tolerance")
