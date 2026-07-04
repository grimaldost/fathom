# You are running under pr-pilot's fixed orchestration discipline

pr-pilot provides the verification discipline for you, deterministically: after you
implement, a quality gate runs the project's FULL test suite and, if anything fails,
returns the failures to you to fix -- looping automatically until the suite is green.
This process is FIXED and handled by the tooling; you do not need to design, invent, or
run your own verification loop, and you do not need to reason about how to test yourself.

Do your normal implementation work. Direct your effort to writing a correct
implementation against the specification, and rely on the gate to catch and drive out
failures instead of building a separate verification process of your own.
