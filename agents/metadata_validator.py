"""
Metadata Validator Agent
-------------------------
Checks each content record against required metadata fields and flags
missing, blank, or malformed values. This is a rules-based agent (no LLM
call needed) since metadata completeness is a deterministic check -- but
it's built as a standalone "agent" module so the orchestrator can treat
it identically to the LLM-backed agents.
"""

import json
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_requirements():
    with open(DATA_DIR / "launch_requirements.json") as f:
        return json.load(f)


def load_metadata():
    return pd.read_csv(DATA_DIR / "content_metadata.csv")


def validate_row(row, required_fields):
    """Return a list of issues found for a single content row."""
    issues = []

    for field in required_fields:
        value = row.get(field)
        if pd.isna(value) or str(value).strip() == "":
            issues.append({
                "field": field,
                "issue": f"Missing required field: '{field}'",
                "severity": "high" if field in ("content_rating", "release_date") else "medium"
            })

    # Malformed / logic checks beyond simple blanks
    if not pd.isna(row.get("runtime_minutes")):
        try:
            runtime = float(row["runtime_minutes"])
            if runtime <= 0:
                issues.append({
                    "field": "runtime_minutes",
                    "issue": "Runtime is zero or negative",
                    "severity": "high"
                })
        except (ValueError, TypeError):
            issues.append({
                "field": "runtime_minutes",
                "issue": "Runtime is not a valid number",
                "severity": "high"
            })

    artwork_status = str(row.get("artwork_status", "")).strip().lower()
    if artwork_status in ("missing", "pending", "nan", ""):
        issues.append({
            "field": "artwork_status",
            "issue": f"Artwork status is '{artwork_status}', not approved",
            "severity": "critical" if artwork_status == "missing" else "medium"
        })

    return issues


def run():
    """Run metadata validation across all content and return structured results."""
    requirements = load_requirements()
    df = load_metadata()
    required_fields = requirements["required_metadata_fields"]

    results = []
    for _, row in df.iterrows():
        issues = validate_row(row, required_fields)
        results.append({
            "content_id": row["content_id"],
            "title": row.get("title", "Unknown"),
            "issue_count": len(issues),
            "issues": issues,
            "status": "FAIL" if any(i["severity"] in ("critical", "high") for i in issues)
                      else ("WARN" if issues else "PASS")
        })

    return results


if __name__ == "__main__":
    for r in run():
        print(f"{r['content_id']} ({r['title']}): {r['status']} - {r['issue_count']} issue(s)")
        for issue in r["issues"]:
            print(f"    [{issue['severity'].upper()}] {issue['issue']}")
