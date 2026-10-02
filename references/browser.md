# Browser — jev-qa mapped to native tools, upgraded with jev-ultrafast's loop

jev-harness's Browser QA pairs `jev-ultrafast` (the browser-use Python
library) with the `jev-qa` reviewer agent. This runtime doesn't install the
library — the capability is native — but I studied jev-ultrafast
(`browser-use/jev-ultrafast`, 2026-10-02) and ported its *decision loop*,
which is where its speed comes from: 7.1s for a Google Flights search,
25% faster than the baseline in matched runs, 1,092 → 101 browser protocol
calls. The wins are all policy, no special hardware:

- **One observation → one decision → one action.** Never plan a blind chain;
  re-observe after every action.
- **Structured state, not screenshots, drives decisions.** Text/DOM first;
  screenshots only for final visual verification or explicit recording.
- **Bounded waits.** Don't wait on animations. Wait only for an absent or
  disabled control, or results still loading — and cap it.
- **Never repeat a mutation.** If an action didn't change the page, don't
  run it again. Three no-change actions in a row = BLOCKED, stop.
- **DONE needs independent evidence.** Claiming done is not proof; the
  report must quote the observed URL, text, or element state.

## The ladder (fast → heavy)

1. **`browser.search`** — information lookup. One call, text results.
   Default for "find out X".
2. **`browser.open`** — read a page's text. For when search snippets aren't
   enough. Still cheap.
3. **`browser.spawn_task`** — a live Chromium I instruct: navigate, click,
   fill forms, scroll, screenshot. Heavy (its own agent turn). Only when
   the task needs *interaction* or *visual verification*.

A question answerable from text never earns a live browser. Parallelize
independent lookups: one scout subagent per question.

## The Jev-driven loop — `mbrowser.py` + one steered browser session

For interaction-heavy tasks, I run jev-ultrafast's actual architecture: **Jev
picks the operation + target each step; I execute via the browser.** The
decider is `bin/mbrowser.py` (ports `model.py`: `choice`-type operation and
per-operation target heads, `validate_choice`, the NEXT_ACTION/TARGET rules).

The loop (I drive it; the browser session stays alive across steps):

1. **Spawn.** `browser.spawn_task`: "Open <URL>. Report the page title, URL,
   a visible-text excerpt, and EVERY interactive element as an indexed table:
   `[n] role · label · current value`. Then STOP — act on nothing, wait for
   my next instruction."
2. **Decide.** Save its table as JSON, run
   `mbrowser.py decide --goal "<goal>" --page page.json --elements
   elements.json --history history.json`. Jev returns one operation +
   target (single request, ~1.6k tokens).
3. **Act.** `browser.steer_task` with that ONE action:
   - `CLICK [n]` → "Click element [n] (<label>)."
   - `TYPE_TEXT [n]` → I write the value myself from the goal/values map
     (I play jev-ultrafast's text helper; never invent personal data), then
     "Type '<text>' into element [n]."
   - `SELECT [n]` / `SCROLL_UP` / `SCROLL_DOWN` / `WAIT` → as named.
   - `DONE` → I verify the quoted evidence myself; the task's claim is not
     proof. `BLOCKED` → stop and report.
4. **Re-observe.** Steer: "Report the indexed table again, plus whether the
   page changed." Back to step 2.
5. **Guards.** Max N steps (10–25 sane); never repeat an action that changed
   nothing; 3 no-change actions in a row = stop as BLOCKED.

This loop is for interaction-heavy work where Jev's per-step judgment pays
off. Simple lookups stay on the ladder above — a full loop for "find out X"
would be ceremony, not speed.

## QA flows (jev-qa role)

Same loop, plus a step list: URLs, viewports if they matter, what to
click/type (fake values only), what must appear, what to screenshot. The
report follows the terse protocol: STATUS + checks + pass/fail + evidence
(screenshot paths or quoted text). I verify the evidence myself; the task's
DONE is a claim, not a proof.
