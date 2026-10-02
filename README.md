# muse-jev

The portable half of [jev-harness](https://github.com/dansya-arsana/jev-harness),
adapted for AI agents **without** Claude Code hooks: heuristic + Jev-backed task
routing, effort-tiered subagent delegation, a dedupe ledger, schema-validated
handoffs, terse STATUS reports, failure-category escalation, and a Jev-driven
browser loop ported from [jev-ultrafast](https://github.com/browser-use/jev-ultrafast).

Built by Muse (Meta's personal agent) at the repo owner's request, as the
"Muse version" of jev-harness. Full merge notes: [`references/merge-notes.md`](references/merge-notes.md).

## What's inside

| Path | What |
|---|---|
| `SKILL.md` | The operating skill: workflow, output contract, rules |
| `bin/mroute.py` | Task router: `fast` / `planned` / `direct`. Heuristic by default, `--jev` for real Jev signals |
| `bin/mjev.py` | Jev (TypeSafe) API client: `POST https://api.typesafe.ai/v1/systemone` |
| `bin/mbrowser.py` | Jev-driven browser decider: picks one operation + target per step |
| `bin/mledger.py` | Subgoal dedupe ledger (`dedupe` / `done` / `list`) |
| `bin/mhandoff.py` | Validate handoff JSON against the jev-harness schemas |
| `bin/mreport.py` | Lint terse `STATUS: DONE` / `STATUS: BLOCKED` agent reports |
| `schemas/` | Handoff contracts, copied unchanged from jev-harness |
| `references/` | Roles, escalation table, browser loop, merge notes |

## Requirements

- Python 3.9+, no third-party packages needed (`jsonschema` optional — without
  it, handoff validation falls back to required-field checks).
- A [TypeSafe API key](https://console.typesafe.ai) for the `--jev` features,
  as `TYPESAFE_API_KEY`. Everything else works without it (conservative
  heuristic routing).

## Quick start

```bash
git clone https://github.com/dansya-arsana/muse-jev.git && cd muse-jev
export TYPESAFE_API_KEY=ts-...   # or add to ~/.config/typesafe/.env

# Route a task (heuristic)
python3 bin/mroute.py route "fix the typo in the README header" --files README.md

# Route with real Jev signals (keyword blockers stay as hard vetoes)
python3 bin/mroute.py route "redesign the auth module" --jev

# Track subgoals without redoing work
python3 bin/mledger.py dedupe "split the refactor into subtasks"
python3 bin/mledger.py done S-001

# Validate a handoff / lint a report
python3 bin/mhandoff.py validate --kind completion handoff.json
python3 bin/mreport.py lint report.txt
```

## The Jev-driven browser loop

`mbrowser.py` ports jev-ultrafast's decision core: Jev picks one browser
operation (`CLICK`, `TYPE_TEXT`, `SELECT`, `SCROLL_UP/DOWN`, `WAIT`, `DONE`,
`BLOCKED`) plus its target from an indexed element table, in a single
TypeSafe request. The agent executes that one action in its own browser,
re-observes, and repeats — bounded steps, no repeated mutations, `DONE`
requires independently quoted evidence. See [`references/browser.md`](references/browser.md).

```bash
python3 bin/mbrowser.py decide --goal "Search for X. Stop when results are visible." \
  --page page.json --elements elements.json --history history.json
```

## Design notes

- **Jev answers the small questions, scripts hold the policy.** Keyword
  blockers (ported verbatim from jev-harness's `fast_path_check`) are hard
  vetoes; Jev supplies depth/breadth/signals.
- **No silent substitution.** A role that can't be filled stops the task.
- **Handoffs are artifacts**, validated against JSON schemas, not vibes.
- **Escalate by failure category**, never by guessing: bad plan → replan,
  hard bug → dig deeper, ambiguous requirement → stop and ask.

## Credits

- Routing policy, schemas, escalation table: [dansya-arsana/jev-harness](https://github.com/dansya-arsana/jev-harness) (MIT)
- Browser decision loop: [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)
- Jev decision model: [TypeSafe](https://docs.typesafe.ai)

## License

MIT — see [LICENSE](LICENSE).
