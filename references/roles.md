# Roles — jev-harness roles mapped to Muse subagents

The nine `jev-*` roles are Claude Code agent definitions pinned to Anthropic
models. On the Muse runtime the *roles* survive; the *models* don't. Map each
role to a `subagent.spawn` brief instead. One model serves all roles here
(the 9Router `muse` combo), so "effort" becomes **brief tightness**: low =
narrow task + strict done-criteria; high = room to investigate and propose.

| jev role | Effort | Write? | Muse equivalent | Use for |
|---|---|---|---|---|
| scout | low | read-only | subagent, tight brief | repo/file/symbol lookup, web lookups |
| analyst | high | read-only | subagent, roomy brief | investigation, code analysis. **Not a reviewer** |
| advisor | high | read-only | subagent, roomy brief | design alternatives + a recommendation |
| architect | high | read-only | subagent, roomy brief | planning only; returns plan text, never writes |
| builder | low | write | subagent, tight brief | default implementation of a plan or fast-path task |
| engineer | medium | write | subagent, medium brief | complex implementation, builder escalation |
| debugger | high | write | main agent or subagent, roomy brief | hard debugging, last-resort rescue |
| reviewer | medium | read-only | subagent, medium brief | independent review of the diff (never analyst as stand-in) |
| qa | low | verify | subagent + browser tools | verification: run it, check it, screenshot it |

Rules (ported from the dispatch guard):
- Read-only roles never get write tools. A read-only task never escalates into a writer.
- Writers run one at a time on the same files; readers run in parallel.
- No silent substitution: if a role can't be filled, stop and say so.
- Non-trivial changes end with reviewer; reviewer verdict `changes_required`
  goes back to builder, `pass` goes to qa.
