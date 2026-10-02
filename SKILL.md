---
name: "muse-jev"
description: "Route and delegate multi-step work the jev-harness way on the Muse runtime: heuristic fast/planned/direct routing, effort-tiered subagent delegation, dedupe ledger, schema-validated handoffs, terse STATUS reports, and escalation by failure category. Use when a task has several parts, before spawning subagents, or when an attempt keeps failing. Triggers: route this, split this into subagents, delegate with jev."
---

# muse-jev

A port of the portable half of `dansya-arsana/jev-harness` for hosts without
Claude Code hooks or a TypeSafe key. **I answer the small questions, the
scripts hold the policy.** Helpers in `bin/` (all dependency-free):

- `mroute.py route "TASK" [--files a,b] [--writes|--no-writes] [--read-only] [--jev]`
- `mjev.py ask "TASK" [--context TEXT]` (Jev API client; needs the stored
  `custom.typesafe` credential)
- `mledger.py dedupe|done|list` (subgoal ledger, `./.muse-jev/subgoals.jsonl`)
- `mhandoff.py validate --kind plan|completion|failure|review|qa FILE`
- `mreport.py lint FILE` (terse STATUS report check)
- `mbrowser.py decide --goal ... --page/--elements/--history ...` (Jev picks
  one browser operation + target per step; I execute via a steered browser
  session — see `references/browser.md`)

Browser capability is native (no install): `browser.search` and
`browser.open` for lookup, `browser.spawn_task` (live Chromium) only when
interaction or visual verification is needed. Full policy:
`references/browser.md`.

## Purpose

Make multi-step work cheaper and more reliable: trivial work skips ceremony,
real work gets a plan + the right subagent + a validated handoff, and failures
escalate by category instead of by guessing.

## Workflow

1. **Route.** `bin/mroute.py route "<task>"`. It prints one JSON object with
   `route`, `checks`, `failed`, `sequence` and `next_agent`.
   - `fast`: do it myself, directly. No subagent, no plan doc.
   - `planned`: split into subtasks that stand alone (what, where, done-when).
     Dedupe each with `mledger.py dedupe`. Spawn per `sequence`: architect
     (plan only, read-only) → builder → reviewer; qa when something runs.
     Persist the plan; hand it to the builder by path.
   - `direct`: read-only. Answer from lookup (scout) or a direct read.
2. **Brief.** Every `subagent.spawn` carries the full brief: task, the plan
   path if any, the files it may touch, and the done-criteria. Readers run in
   parallel; writers run one at a time on the same files. See
   `references/roles.md` for the role map.
3. **Handoffs are artifacts.** Subagents report in the terse protocol
   (`STATUS: DONE` + CHANGED/WHY/TEST/RISK/NEXT, or `STATUS: BLOCKED` +
   CATEGORY/FOUND/EVIDENCE/NEXT). Lint with `mreport.py lint`; validate JSON
   handoffs with `mhandoff.py validate`. Persisted docs stay normal prose.
4. **Escalate by category** (`references/escalation.md`). Guardrails: max 2
   replans, max 2 debugger attempts per task — then stop and report to the user.
5. **Close.** `mledger.py done <id>` per finished subgoal. "Done" means the
   real check passed (tests green / build succeeds / page verified).

## Output contract

- One JSON object per script call; scripts never print anything else on stdout.
- Subagent prompts always include: task, done-criteria, file scope, and the
  plan path when routed `planned`.
- No silent substitution: a role I can't fill stops the task with an explanation.

## Operating rules

- Don't route trivial one-step requests; this skill is for multi-part work.
- Show the routing table (subtask → route, role, why) before spawning 3+
  subagents.
- Confirm destructive / outward-facing actions first; never expose secrets.
- Browser ultrafast policy: `browser.search`/`browser.open` first;
  `browser.spawn_task` only for interaction or screenshots; parallelize
  independent lookups via scout subagents (see `references/browser.md`).
- If a TypeSafe key is connected (stored as `custom.typesafe`), `mroute.py
  --jev` calls Jev for depth/breadth/signals and keeps the keyword blockers
  as hard vetoes; on Jev failure it falls back to heuristics with a
  `jev_fallback` note. Verified live 2026-10-02 (~760 input tokens/call).

## References

- `references/roles.md` — the nine jev roles mapped to subagent briefs.
- `references/browser.md` — jev-qa mapped to native browser tools + ultrafast policy.
- `references/escalation.md` — failure categories and guardrails.
- `references/merge-notes.md` — what was ported, what was dropped, and how
  to merge this back into jev-harness upstream.
- `schemas/` — handoff contracts, copied unchanged from jev-harness.
