# MERGE NOTES — muse-jev: a jev-harness port for the Muse (Meta) runtime

Target repo: `dansya-arsana/jev-harness`. Author of this port: Muse, at the
request of the repo owner (2026-10-02). Purpose: run the jev-harness decision
patterns on a host that is not Claude Code, without the TypeSafe API key.

## What this is

`~/workspace/skills/muse-jev/` is a self-contained port of the *portable*
half of jev-harness: the routing policy, the role taxonomy, the handoff
contracts, the escalation table, and the terse-report protocol. It deliberately
does **not** port the Claude Code half (PreToolUse/UserPromptSubmit hooks, the
nine pinned `jev-*` agent files, `onboard.py`).

## Kept (ported 1:1 where possible)

- `bin/mroute.py` — `fast_path_check()` keyword blockers (`FAST_BLOCKERS`,
  `AMBIGUITY`) copied verbatim from `skill/jev-orchestrator/scripts/jev.py`.
  Jev signal scores (`design`, `self_contained`, `high_stakes`, `depth`,
  `breadth`) are replaced by conservative heuristics (word count, file count,
  explicit `--read-only`); anything unclear falls to the planned route.
- `schemas/` — the five `config/schemas/*.json` contracts copied unchanged.
  `bin/mhandoff.py` validates against them with `jsonschema` (stdlib-style
  required-field fallback if it's missing).
- `bin/mreport.py` — the `STATUS: DONE / BLOCKED` terse-report lint
  (`jev.py report lint`).
- `bin/mledger.py` — the `dedupe / done / list` subgoal ledger
  (`./.muse-jev/subgoals.jsonl`, same shape as `.jev/subgoals.jsonl`).
- `references/escalation.md` — the six failure categories and guardrails
  (max 2 replans, max 2 debugger attempts), unchanged.

## Changed (and why)

- **Roles → briefs, not agents.** The nine `jev-*` agents are Claude Code
  definitions pinned to `claude-opus-5-5` / `claude-sonnet-5-5`. On this host
  one model serves every role, so `references/roles.md` maps each role to a
  `subagent.spawn` brief pattern; "effort" becomes brief tightness
  (low = narrow task + strict done-criteria). No model routing, no aliases,
  no dispatch guard — there is no Agent tool to guard.
- **No hooks.** `permission_gate.py` / `prompt_router.py` / `dispatch_router.py`
  have no equivalent entry point on this runtime (no PreToolUse /
  UserPromptSubmit). The *policy* they encode is kept as operating rules in
  `SKILL.md` instead (confirm destructive actions, never expose secrets,
  route before spawning).
- **Browser QA → native tools.** jev-harness drives UI checks with
  jev-ultrafast (browser-use) + the `jev-qa` agent. This port maps that role
  to the runtime's native browser tools instead (`references/browser.md`):
  `browser.search`/`browser.open` for lookup, `browser.spawn_task` (live
  Chromium) for interaction and screenshots. Deliberately no browser-use
  install: for info retrieval the native tools are faster, and scripted QA
  flows are expressible as explicit `spawn_task` step lists. If upstream
  ever wants the real jev-ultrafast suite, `hosts/muse/` is where its
  scenario-runner equivalent would live.
- **jev-ultrafast loop studied (2026-10-02).** Read `browser-use/jev-ultrafast`
  (agent.py, questions.py, snapshot.js, performance.md). Its speed comes from
  policy, not hardware: one observation → one decision → one action; indexed
  element tables instead of screenshots in the loop; bounded waits (never on
  animation); no repeated mutations; 3 no-change actions → BLOCKED; DONE
  requires independent evidence. **Then implemented for real:** `bin/mbrowser.py`
  ports `model.py`'s Jev operation/target heads (`choice` type,
  `validate_choice`, NEXT_ACTION/TARGET rules) over the stored `custom.typesafe`
  credential; the main agent runs the loop by steering one live browser session
  (observe → `mbrowser.py decide` → steer single action → re-observe).
  Verified: TYPE_TEXT→search box (conf 0.99), DONE on visible results (conf
  0.96), ~1.6k tokens/decision. Not ported: the CDP snapshot reader (needs the
  library) and the separate text-helper model (the main agent writes field
  values directly).
- **No Jev calls** (at port time). `jevlib.ask()` needs `TYPESAFE_API_KEY`; none was
  configured here. `mroute.py` was the heuristic fallback the SKILL.md itself
  prescribes when Jev is unavailable. **Update 2026-10-02:** the owner connected
  TypeSafe via the `custom.typesafe` connector; `bin/mjev.py` now calls
  `POST https://api.typesafe.ai/v1/systemone` through the authd surrogate
  exchange (raw key never visible), and `mroute.py --jev` uses real Jev
  signals for depth/breadth/design/self_contained/unknown_cause/high_stakes
  with the keyword blockers as hard vetoes. Verified live: typo fix → fast
  (depth 0.17), auth redesign → planned (depth 2.93, design 0.91), ~760 input
  tokens per call.

## Suggested upstream integration

1. **Host table** (`README.md`): add a `Muse (Meta)` row — gate hook:
   unverified, prompt hook: unverified, subagents: partial (own format),
   skills: full, rules file: full, permission/model config: partial. Source
   row for `docs/jev/host-research.md`.
2. **New dir** `hosts/muse/` holding this skill verbatim, plus a
   `hosts/muse/README.md` pointing at these merge notes. Keeps the Claude
   Code path untouched; `onboard.py` keeps detecting-and-skipping as today.
3. **Evals**: the heuristic router can be scored against
   `evals/route_fastpath_cases.jsonl` (12 cases) — expected: high precision
   on "planned", lower recall on "fast" than the Jev-backed router, by design.

## Test evidence (2026-10-02)

- `python3 -m py_compile bin/*.py` — clean.
- `mroute.py route` on: trivial one-file fix → `fast`; "redesign the auth
  module" → `planned` (architecture_change); "where is the retry logic?" →
  `direct`; "migrate the database schema" → `planned` (schema_change).
- `mledger.py dedupe/done/list` round-trip on a temp ledger — ok.
- `mhandoff.py validate` on a valid/invalid completion doc — ok/rejected.
- `mreport.py lint` on DONE/BLOCKED samples — ok; missing-field sample rejected.

## Open items for the owner

- ~~Send `TYPESAFE_API_KEY` when ready~~ — **done 2026-10-02.** Key connected
  via `custom.typesafe` connector (secure vault, bearer_header on
  api.typesafe.ai). `mroute.py --jev` verified live against the real API.
- Decide: merge as `hosts/muse/`, or keep as a separate companion repo.
