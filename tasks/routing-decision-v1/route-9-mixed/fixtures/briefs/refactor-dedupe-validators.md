The `forms` package carries three near-identical copies of the same address rules,
one in each of `forms/signup.py`, `forms/profile.py` and `forms/invite.py`. They have
drifted apart: each copy enforces a different subset of the rules written down in
`RULES.md`.

Remove the duplication. Put one implementation of the rules in `forms/common.py` as
`check_email(email)`, have all three of `validate_signup`, `validate_profile` and
`validate_invite` call it, and make every form agree with `RULES.md` — the same
answer for the same address, on the valid and invalid examples RULES.md lists and on
anything else the four rules cover.

Those four files are the only ones to change. Keep the three public function names and
their signatures, and keep the shipped test suite passing.
