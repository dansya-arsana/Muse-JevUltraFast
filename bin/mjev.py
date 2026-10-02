#!/usr/bin/env python3
"""mjev: Jev (TypeSafe) decision client for the muse-jev skill.

POSTs to https://api.typesafe.ai/v1/systemone with the stored
`custom.typesafe` credential via the authd surrogate exchange. The raw key
is never visible here: only `hsurr:*` surrogates leave this process.

Usage:
    mjev.py ask "TASK" [--context TEXT] [--timeout SEC]

Prints one JSON object: {"answers": {...}, "usage": {...}}.
Question set is the fast-path subset: depth, breadth, design,
self_contained, unknown_cause, high_stakes.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
try:
    import dynamic_credentials as dc
    _HAVE_SURROGATE = True
except ImportError:
    dc = None
    _HAVE_SURROGATE = False

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
ALLOWED_HOSTS = ["api.typesafe.ai"]
CREDENTIAL = "custom.typesafe"  # Hatch Secure Vault connector name

_SECRET_PATTERNS = [
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1<redacted>"),
    (re.compile(r"(?i)\b(sk|pk|rk|ghp|gho|github_pat|xox[abpr])[-_][A-Za-z0-9_-]{8,}"), "<redacted>"),
    (re.compile(r"(?i)((?:api[_-]?key|token|secret|password|passwd|auth)[\"']?\s*[:=]\s*[\"']?)[^\s\"'&]{4,}"),
     r"\1<redacted>"),
]


def redact(text):
    if not isinstance(text, str):
        return text
    for pat, repl in _SECRET_PATTERNS:
        text = pat.sub(repl, text)
    return text


def noul(instructions, yes, no):
    return {"type": "noul", "instructions": instructions,
            "criteria": {"true": yes, "false": no}}


QUESTIONS = {
    "depth": {
        "type": "score",
        "instructions": "How much careful reasoning does `task` need to be done correctly?",
        "criteria": [
            "Mechanical: a lookup, search, rename, formatting, or version bump with no judgment",
            "Clear change: the fix or edit is known and touches one or two files",
            "Multi-part: coordinated changes across several files, or a bug whose cause is already known",
            "Hard: unknown root cause, design decisions, concurrency, security, or subtle correctness",
        ],
    },
    "breadth": {
        "type": "score",
        "instructions": "How much of the codebase does `task` span, i.e. how many files or areas must be read or changed?",
        "criteria": [
            "One file",
            "A few related files",
            "One subsystem or module",
            "Many subsystems or the whole codebase",
        ],
    },
    "self_contained": noul(
        "Could a fresh assistant do `task` well given only the task text and the repository, without the main agent's conversation history?",
        "The task names what to do and where; the repository is enough",
        "It depends on decisions, findings, or preferences only present in the main conversation"),
    "unknown_cause": noul(
        "Is `task` debugging or investigating a problem whose cause is not yet known?",
        "The cause must be found", "The cause or the needed change is already known"),
    "design": noul(
        "Does `task` require choosing between approaches or designing architecture or interfaces?",
        "An approach must be chosen or an architecture/interface designed",
        "The approach is already decided; it only needs to be carried out"),
    "high_stakes": noul(
        "If `task` were done slightly wrong, could the result be a security hole, leaked secrets, lost or corrupted data, "
        "wrong money amounts, or a production outage? Judge the consequences of a mistake, not the topic.",
        "A plausible mistake would cause a security, data, money, or outage problem",
        "A plausible mistake would be a visible bug that is cheap to notice and fix"),
}


class JevError(RuntimeError):
    pass


def ask(task, context="", timeout=30.0, retries=2):
    """Router question set (depth/breadth/signals). Returns the parsed response dict."""
    state = {"task": redact(task), "context_from_main_agent": redact(context or "")}
    return ask_questions(QUESTIONS, state, timeout, retries)


def _auth_headers():
    """Bearer headers via Hatch surrogate, else TYPESAFE_API_KEY env (portable)."""
    if _HAVE_SURROGATE:
        return None  # applied per-request via add_surrogate_to_request
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key:
        raise JevError("no credential: Hatch surrogate unavailable and TYPESAFE_API_KEY not set")
    return {"Authorization": "Bearer " + key}


def ask_questions(questions, state, timeout=30.0, retries=2):
    """One /v1/systemone request with caller-built questions/state. Returns parsed dict."""
    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
    headers = {"Content-Type": "application/json"}
    static_auth = _auth_headers()
    if static_auth:
        headers.update(static_auth)
    req = urllib.request.Request(API_URL, data=body, headers=headers)
    if _HAVE_SURROGATE:
        try:
            dc.add_surrogate_to_request(req, CREDENTIAL, allowed_hosts=ALLOWED_HOSTS)
        except dc.DynamicCredentialError as e:
            raise JevError("credential unavailable: %s" % e)
    last = "unknown error"
    for attempt in range(max(1, retries)):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return dc.read_json_response(resp)
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode(errors="replace")[:300]
            except Exception:
                detail = ""
            last = "HTTP %d: %s" % (e.code, detail)
            if e.code == 429 or e.code >= 500:
                if attempt + 1 < retries:
                    time.sleep(min(2 ** attempt, 5))
                continue
            raise JevError(last)
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = "connection failed: %s" % (getattr(e, "reason", None) or e)
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 5))
    raise JevError(last)


def main(argv):
    if len(argv) < 2 or argv[0] != "ask":
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    task, context, timeout = argv[1], "", 30.0
    i = 2
    while i < len(argv):
        if argv[i] == "--context" and i + 1 < len(argv):
            context, i = argv[i + 1], i + 2
        elif argv[i] == "--timeout" and i + 1 < len(argv):
            timeout, i = float(argv[i + 1]), i + 2
        else:
            i += 1
    try:
        print(json.dumps(ask(task, context, timeout), indent=2, ensure_ascii=False))
    except JevError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
