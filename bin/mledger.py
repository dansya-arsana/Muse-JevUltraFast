#!/usr/bin/env python3
"""mledger: subgoal dedupe ledger for the muse-jev skill.

Ports jev.py's dedupe/done/list. One JSON object per line in
./.muse-jev/subgoals.jsonl (override with --ledger PATH).

Usage:
    mledger.py dedupe "SUBTASK" [--ledger PATH]   # new -> registers; existing -> reports duplicate_of
    mledger.py done ID [--ledger PATH]            # mark subgoal finished
    mledger.py list [--ledger PATH]               # show ledger
"""
import json
import os
import sys
import time

DEFAULT_LEDGER = os.path.join(os.getcwd(), ".muse-jev", "subgoals.jsonl")


def load(path):
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return rows


def save(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def norm(s):
    return " ".join((s or "").strip().lower().split())


def main(argv):
    if not argv or argv[0] not in ("dedupe", "done", "list"):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    cmd = argv[0]
    ledger = DEFAULT_LEDGER
    rest = []
    i = 1
    while i < len(argv):
        if argv[i] == "--ledger" and i + 1 < len(argv):
            ledger, i = argv[i + 1], i + 2
        else:
            rest.append(argv[i]); i += 1
    rows = load(ledger)

    if cmd == "dedupe":
        if not rest:
            print("dedupe needs a subtask string", file=sys.stderr); return 2
        sub = " ".join(rest)
        key = norm(sub)
        for r in rows:
            if norm(r.get("subtask", "")) == key:
                print(json.dumps({"duplicate_of": r["id"], "status": r.get("status"),
                                  "subtask": r["subtask"]}, indent=2, ensure_ascii=False))
                return 0
        rid = "S-%03d" % (len(rows) + 1)
        rows.append({"id": rid, "subtask": sub, "status": "open", "ts": int(time.time())})
        save(ledger, rows)
        print(json.dumps({"registered": rid, "duplicate_of": None, "subtask": sub},
                         indent=2, ensure_ascii=False))
        return 0

    if cmd == "done":
        if not rest:
            print("done needs an ID", file=sys.stderr); return 2
        rid = rest[0]
        for r in rows:
            if r["id"] == rid:
                r["status"] = "done"
                save(ledger, rows)
                print(json.dumps({"marked_done": rid}, indent=2)); return 0
        print(json.dumps({"error": "unknown id", "id": rid})); return 1

    # list
    print(json.dumps({"ledger": ledger, "subgoals": rows}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
