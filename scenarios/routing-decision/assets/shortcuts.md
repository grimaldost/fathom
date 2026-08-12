# Routing policy

Decide the tier by **shape**, then apply the **floor**. There is no scoring and no
arithmetic: if you find yourself adding numbers, you are using the wrong policy.

## Shape lookup

| the task is | tier |
|---|---|
| a config, version, label or text edit with no logic | `weak` |
| a fix inside one named function, with the fix site named in the brief | `weak` |
| a test for behaviour that already exists, cases given | `weak` |
| a refactor whose edit sites the brief enumerates | `mid` |
| a feature or endpoint that follows a pattern already in the codebase | `mid` |
| a bug whose cause is somewhere other than where the symptom shows | `mid` |
| a review, a plan, or an ordering against constraints the brief states | `mid` |
| two code paths, backends or dialects that must produce the same answer | `strong` |
| a change to shared code whose callers the brief does not all name | `strong` |
| novel design, concurrency, security-critical, or an interface that is hard to reverse | `strong` |

Read the brief for the shape, not for how long it is. Length is not difficulty.

## The floor

Applied after the lookup. It only ever raises a tier, never lowers one.

- The brief does not name every site that has to change → not below `mid`.
- The work is hard to reverse, or nothing will automatically check it → not below `mid`.
- Two implementations have to agree with each other → not below `strong`.

## Ties

Torn between two tiers: take the **cheaper** one when a test or a gate will catch a
wrong answer, and the **dearer** one when nothing will. A retry you can detect is
cheap; a wrong answer nobody checks is not.

## Output

One tier per brief. Do not show your reasoning unless asked — the tier is the answer.
