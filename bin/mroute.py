#!/usr/bin/env python3
"""mroute: task router for the muse-jev skill.

Ports jev-harness's fast_path_check() keyword blockers. Two signal sources:

- heuristic (default): keyword hits + conservative estimates, no network.
- --jev: real Jev (TypeSafe) signals via bin/mjev.py, keyword blockers kept
  as hard vetoes. Falls back to heuristic if Jev is unreachable.

Usage:
    mroute.py route "TASK" [--files a.py,b.py] [--writes | --no-writes] [--read-only]
    mroute.py route "TASK" --jev [--context TEXT]

Output: one JSON object {task_id, route, fast_path, checks, failed, sequence,
next_agent, why}. Routes: fast (do directly) | planned (split, plan,
delegate) | direct (read-only lookup).
"""
import hashlib
import json
import os
import re
import sys

# --- exact ports from jev-harness skill/jev-orchestrator/scripts/jev.py ---
FAST_BREADTH_MAX = 0.75  # breadth score: 0 = "One file", 1 = "A few related files"
FAST_SIGNAL_MAX = 0.4    # design / high_stakes / unknown_cause must be clearly low
FAST_CLEAR_MIN = 0.6     # P_YES: self_contained must clearly hold
DEPTH_ENGINEER = 1.5

FAST_BLOCKERS = {
    "architecture_change": re.compile(
        r"\b(architect\w*|redesign|re-architect|new (module|service|subsystem|layer)|module boundar\w*|"
        r"cross[- ]module|state machine|framework|dependency injection|plugin system)\b", re.I),
    "schema_change": re.compile(
        r"\b(schema|migrations?|migrate|database|db|sql|tables?|columns?|index(es)?|orm|proto(buf)?)\b", re.I),
    "persistence_change": re.compile(
        r"\b(persist\w*|storage|store[sd]?|save (format|file|data)|serializ\w*|deserializ\w*|cache|caching|"
        r"disk|file format|local ?storage|session storage|cookies?)\b", re.I),
    "public_api_change": re.compile(
        r"\b(public api|api|endpoints?|signatures?|interfaces?|exported|exports?|breaking|sdk|"
        r"contract|protocol|webhooks?|graphql|rest)\b", re.I),
    "concurrency_change": re.compile(
        r"\b(concurren\w*|threads?|threading|race|races|locks?|locking|mutex\w*|async\w*|await|"
        r"parallel\w*|deadlocks?|atomic\w*|coroutines?|workers?|queues?)\b", re.I),
    "security_or_network": re.compile(
        r"\b(auth\w*|security|secrets?|tokens?|passwords?|crypto\w*|permissions?|payments?|"
        r"network\w*|sockets?|http client|retry|retries|production|prod deploy)\b", re.I),
}
AMBIGUITY = re.compile(
    r"\b(maybe|somehow|not sure|unclear|figure out|tbd|decide|which (approach|way|option)|"
    r"or should|what'?s the best|not certain)\b|\?", re.I)

READONLY_HINT = re.compile(
    r"\b(find|search|look ?up|check|read|inspect|analyze|analyse|explain|list|show|what|where|which|how does)\b", re.I)
WRITE_HINT = re.compile(
    r"\b(create|write|implement|build|fix|edit|update|delete|remove|refactor|add|change|deploy|install|migrate)\b", re.I)


def make_task_id(task):
    return "T-" + hashlib.sha1((task or "").strip().lower().encode("utf-8")).hexdigest()[:8]


def fast_path_check(task, signals, depth, breadth, files=None, writes=True):
    """Exact port of jev-harness fast_path_check()."""
    sig = signals or {}
    depth = depth if depth is not None else 9
    breadth = breadth if breadth is not None else 9
    files = [f for f in (files or []) if f]
    single = (len(files) == 1 and breadth < 1.0) if files else breadth < FAST_BREADTH_MAX
    hits = {k: bool(rx.search(task or "")) for k, rx in FAST_BLOCKERS.items()}
    checks = {
        "single_file_expected": single,
        "architecture_change": hits["architecture_change"] or sig.get("design", 1) >= FAST_SIGNAL_MAX,
        "schema_change": hits["schema_change"],
        "persistence_change": hits["persistence_change"],
        "public_api_change": hits["public_api_change"],
        "concurrency_change": hits["concurrency_change"],
        "requirements_clear": (sig.get("self_contained", 0) >= FAST_CLEAR_MIN
                               and sig.get("unknown_cause", 1) < FAST_SIGNAL_MAX
                               and not AMBIGUITY.search(task or "")),
        "low_stakes": sig.get("high_stakes", 1) < FAST_SIGNAL_MAX and not hits["security_or_network"],
        "small": depth < DEPTH_ENGINEER,
        "writes": bool(writes),
    }
    want = {"single_file_expected": True, "architecture_change": False, "schema_change": False,
            "persistence_change": False, "public_api_change": False, "concurrency_change": False,
            "requirements_clear": True, "low_stakes": True, "small": True, "writes": True}
    failed = [k for k, v in want.items() if checks[k] != v]
    return not failed, checks, failed


def heuristic_signals(task, files):
    """Conservative signal estimates that reproduce the old heuristic checks."""
    hits = {k: bool(rx.search(task or "")) for k, rx in FAST_BLOCKERS.items()}
    ambiguous = bool(AMBIGUITY.search(task or ""))
    words = len((task or "").split())
    nfiles = len([f for f in (files or []) if f])
    small = words <= 25 and nfiles <= 1
    return {
        "signals": {
            "design": 0.9 if hits["architecture_change"] else 0.1,
            "self_contained": 0.2 if ambiguous else 0.8,
            "unknown_cause": 0.8 if ambiguous else 0.1,
            "high_stakes": 0.9 if hits["security_or_network"] else 0.1,
        },
        "depth": 0.5 if small else 9.0,
        "breadth": 0.2 if nfiles <= 1 else 9.0,
    }


def jev_signals(task, context=""):
    """Real Jev signals. Raises RuntimeError if Jev is unreachable."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mjev
    try:
        r = mjev.ask(task, context)
    except mjev.JevError as e:
        raise RuntimeError("Jev unavailable: %s" % e)
    try:
        a = r["answers"]
        signals = {k: float(a[k]["noul"]) for k in
                   ("design", "self_contained", "unknown_cause", "high_stakes")}
        depth = float(a["depth"]["score"])
        breadth = float(a["breadth"]["score"])
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError("bad Jev answer: %r" % e)
    return {"signals": signals, "depth": depth, "breadth": breadth,
            "jev_tokens": (r.get("usage") or {}).get("input_tokens")}


def route(task, files=None, writes=True, read_only=False, use_jev=False, context=""):
    task_id = make_task_id(task)
    if read_only or (READONLY_HINT.search(task or "") and not WRITE_HINT.search(task or "")):
        return {
            "task_id": task_id, "route": "direct", "fast_path": False,
            "checks": {}, "failed": [],
            "sequence": [{"role": "scout", "effort": "low", "purpose": "read-only lookup/investigation"}],
            "next_agent": "scout",
            "why": "read-only task: answer from lookup, no writes needed",
        }
    jev_used, jev_fallback = False, None
    if use_jev:
        try:
            s = jev_signals(task, context)
            jev_used = True
        except RuntimeError as e:
            s = heuristic_signals(task, files)
            jev_fallback = str(e)
    else:
        s = heuristic_signals(task, files)
    fast, checks, failed = fast_path_check(task, s["signals"], s["depth"], s["breadth"], files, writes)
    out = {"task_id": task_id, "jev": jev_used}
    if jev_fallback:
        out["jev_fallback"] = jev_fallback
    if jev_used:
        out.update({"depth": round(s["depth"], 2), "breadth": round(s["breadth"], 2),
                    "signals": {k: round(v, 2) for k, v in s["signals"].items()}})
        if s.get("jev_tokens") is not None:
            out["jev_tokens"] = s["jev_tokens"]
    if fast:
        out.update({
            "route": "fast", "fast_path": True, "checks": checks, "failed": failed,
            "sequence": [{"role": "builder", "effort": "low", "purpose": "implement the one clear change"}],
            "next_agent": "builder",
            "why": "all fast-path checks hold: single clear low-stakes change",
        })
        return out
    out.update({
        "route": "planned", "fast_path": False, "checks": checks, "failed": failed,
        "sequence": [
            {"role": "architect", "effort": "high", "purpose": "plan first (read-only), persist plan"},
            {"role": "builder", "effort": "low", "purpose": "implement the persisted plan"},
            {"role": "reviewer", "effort": "medium", "purpose": "independent review of the diff"},
        ],
        "next_agent": "architect",
        "why": "failed checks: " + ", ".join(failed),
    })
    return out


def main(argv):
    if len(argv) < 2 or argv[0] != "route":
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    task, files, writes, read_only, use_jev, context = argv[1], [], True, False, False, ""
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == "--files" and i + 1 < len(argv):
            files = [f.strip() for f in argv[i + 1].split(",") if f.strip()]; i += 2
        elif a == "--no-writes":
            writes = False; i += 1
        elif a == "--writes":
            writes = True; i += 1
        elif a == "--read-only":
            read_only = True; i += 1
        elif a == "--jev":
            use_jev = True; i += 1
        elif a == "--context" and i + 1 < len(argv):
            context = argv[i + 1]; i += 2
        else:
            i += 1  # ignore --json and unknown flags
    print(json.dumps(route(task, files, writes, read_only, use_jev, context),
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
