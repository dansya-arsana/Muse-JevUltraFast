#!/usr/bin/env python3
"""mhandoff: validate agent handoff artifacts against jev-harness JSON schemas.

Usage:
    mhandoff.py validate --kind plan|completion|failure|review|qa FILE [--schemas DIR]
    mhandoff.py template --kind plan|completion|failure|review|qa   # print a skeleton

Schemas live in ../schemas/ (copied from jev-harness config/schemas/).
Kinds map: plan->jev_plan, completion/failure->jev_handoff, review->review, qa->qa.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND2SCHEMA = {
    "plan": "jev_plan.schema.json",
    "completion": "jev_handoff.schema.json",
    "failure": "jev_failure.schema.json",
    "review": "review.schema.json",
    "qa": "qa.schema.json",
}

TEMPLATES = {
    "plan": {"task_id": "T-xxxx", "objective": "...", "assumptions": ["..."],
             "constraints": ["..."], "files_to_inspect": ["..."], "likely_files_to_modify": ["..."],
             "implementation_steps": ["1. ... (done when ...)"],
             "invariants": ["..."], "acceptance_criteria": ["..."],
             "escalation_conditions": ["..."]},
    "completion": {"task_id": "T-xxxx", "role": "jev-builder", "status": "completed",
                   "files_changed": ["..."], "implementation_summary": ["..."],
                   "tests_run": ["..."], "test_results": ["..."], "risks": ["..."],
                   "next_recommended_agent": "jev-reviewer"},
    "failure": {"task_id": "T-xxxx", "agent": "jev-builder", "category": "implementation_complexity",
                "completed": ["..."], "blocked_by": ["..."],
                "recommended_route": {"agent": "orchestrator", "reason": "..."},
                "evidence": ["..."]},
    "review": {"task_id": "T-xxxx", "verdict": "pass",
               "findings": {"critical": [], "major": [], "minor": []},
               "acceptance_criteria": [{"criterion": "...", "status": "pass"}],
               "regression_risks": ["..."], "required_changes": ["..."]},
    "qa": {"task_id": "T-xxxx", "verdict": "pass",
           "checks": [{"name": "...", "status": "pass", "evidence": "..."}], "findings": []},
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(doc, schema):
    try:
        import jsonschema
    except ImportError:
        # minimal fallback: required-fields check only
        missing = [k for k in schema.get("required", []) if k not in doc]
        return missing
    validator = jsonschema.Draft7Validator(schema)
    return sorted(validator.iter_errors(doc), key=lambda e: list(e.path))


def main(argv):
    if len(argv) < 2 or argv[0] not in ("validate", "template"):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    cmd = argv[0]
    kind, path, schemas_dir = None, None, os.path.join(BASE, "schemas")
    i = 1
    while i < len(argv):
        if argv[i] == "--kind" and i + 1 < len(argv):
            kind, i = argv[i + 1], i + 2
        elif argv[i] == "--schemas" and i + 1 < len(argv):
            schemas_dir, i = argv[i + 1], i + 2
        elif not argv[i].startswith("--") and path is None:
            path, i = argv[i], i + 1
        else:
            i += 1
    if kind not in KIND2SCHEMA:
        print("kind must be one of: " + ", ".join(KIND2SCHEMA), file=sys.stderr)
        return 2
    if cmd == "template":
        print(json.dumps(TEMPLATES[kind], indent=2, ensure_ascii=False))
        return 0
    if not path:
        print("validate needs a FILE", file=sys.stderr); return 2
    try:
        doc = load_json(path)
        schema = load_json(os.path.join(schemas_dir, KIND2SCHEMA[kind]))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"ok": False, "error": str(e)})); return 1
    errors = validate(doc, schema)
    if not errors:
        print(json.dumps({"ok": True, "kind": kind, "file": path}))
        return 0
    def fmt(e):
        return e if isinstance(e, str) else f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
    print(json.dumps({"ok": False, "kind": kind, "file": path,
                      "errors": [fmt(e) for e in errors]}, indent=2, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
