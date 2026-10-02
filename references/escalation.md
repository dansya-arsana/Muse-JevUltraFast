# Escalation — by failure category, never by substitution

When a subagent reports `STATUS: BLOCKED`, classify first, then act.
Ported from `jev.py escalate`; guardrails: max 2 replans, max 2 debugger
attempts per task. Hit a guardrail → stop and report to the user.

| Category | Next |
|---|---|
| `implementation_complexity` | one step up the ladder: builder → engineer → debugger |
| `hard_debugging` | debugger directly |
| `invalid_plan` | architect replans directly; no engineer/debugger attempt first |
| `requirement_ambiguity` | orchestrator (me): stop coding. Ask the user unless safely inferable |
| `environment_failure` | orchestrator: fix the environment or stop |
| `test_failure` | same coder retries, twice max, then one step up |

Record every escalation (what failed, what was tried, what changed) so the
next attempt doesn't repeat it. The BLOCKED report's EVIDENCE goes to the
next agent verbatim.
