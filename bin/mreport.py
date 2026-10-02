#!/usr/bin/env python3
"""mreport: lint terse STATUS agent reports for the muse-jev skill.

Ports jev.py's `report lint`. A report is either:
    STATUS: DONE     + CHANGED / WHY / TEST / RISK / NEXT
    STATUS: BLOCKED  + CATEGORY / FOUND / EVIDENCE / NEXT

Usage:
    mreport.py lint FILE        # FILE may be text or JSON with a "report" field
    echo "..." | mreport.py lint --stdin
"""
import json
import re
import sys

DONE_FIELDS = ["CHANGED", "WHY", "TEST", "RISK", "NEXT"]
BLOCKED_FIELDS = ["CATEGORY", "FOUND", "EVIDENCE", "NEXT"]
CATEGORIES = {"implementation_complexity", "hard_debugging", "invalid_plan",
              "requirement_ambiguity", "environment_failure", "test_failure"}


def fields_present(text, fields):
    found = {}
    for f in fields:
        m = re.search(rf"^{f}\s*:\s*(.+)$", text, re.M | re.I)
        found[f] = bool(m and m.group(1).strip())
    return found


def lint(text):
    text = text.strip()
    m = re.search(r"^STATUS\s*:\s*(DONE|BLOCKED)\b", text, re.M | re.I)
    if not m:
        return {"ok": False, "errors": ["missing 'STATUS: DONE' or 'STATUS: BLOCKED' line"]}
    status = m.group(1).upper()
    errors = []
    if status == "DONE":
        present = fields_present(text, DONE_FIELDS)
        missing = [f for f, ok in present.items() if not ok]
        if missing:
            errors.append("DONE report missing fields: " + ", ".join(missing))
    else:
        present = fields_present(text, BLOCKED_FIELDS)
        missing = [f for f, ok in present.items() if not ok]
        if missing:
            errors.append("BLOCKED report missing fields: " + ", ".join(missing))
        cm = re.search(r"^CATEGORY\s*:\s*(\S+)", text, re.M | re.I)
        if cm and cm.group(1).strip().lower() not in CATEGORIES:
            errors.append("unknown failure category '%s' (want one of: %s)"
                          % (cm.group(1), ", ".join(sorted(CATEGORIES))))
    return {"ok": not errors, "status": status, "errors": errors}


def main(argv):
    use_stdin, path = False, None
    for a in argv[1:]:
        if a == "--stdin":
            use_stdin = True
        elif path is None and not a.startswith("--"):
            path = a
    if argv[:1] != ["lint"] and not (len(argv) >= 1 and argv[0] == "lint"):
        # allow `mreport.py FILE` as shorthand
        if path is None and argv and not argv[0].startswith("--"):
            path = argv[0]
        elif path is None and not use_stdin:
            print(__doc__.strip().splitlines()[0], file=sys.stderr); return 2
    try:
        text = sys.stdin.read() if use_stdin else open(path, encoding="utf-8").read()
    except OSError as e:
        print(json.dumps({"ok": False, "errors": [str(e)]})); return 1
    text = text.strip()
    if text.startswith("{"):
        try:
            obj = json.loads(text)
            text = obj.get("report", text) if isinstance(obj, dict) else text
        except json.JSONDecodeError:
            pass
    result = lint(text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
