"""
Localization Checker Agent
---------------------------
Cross-checks each title's subtitle/dub language coverage against the
required languages for its release region. Also rules-based (deterministic
comparison against launch_requirements.json), kept as its own agent module
so the orchestrator can call it independently of the LLM-backed triage agent.
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


def parse_lang_list(value):
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [lang.strip().lower() for lang in str(value).split(",")]


def check_row(row, region_requirements):
    region = row.get("release_region")
    reqs = region_requirements.get(region)
    issues = []

    if reqs is None:
        issues.append({
            "issue": f"No launch requirements defined for region '{region}'",
            "severity": "medium"
        })
        return issues

    subs_present = parse_lang_list(row.get("subtitle_languages"))
    dubs_present = parse_lang_list(row.get("dub_languages"))

    missing_subs = [lang for lang in reqs["required_subtitles"] if lang not in subs_present]
    missing_dubs = [lang for lang in reqs["required_dub"] if lang not in dubs_present]

    if missing_subs:
        issues.append({
            "issue": f"Missing required subtitle language(s) for {region}: {', '.join(missing_subs)}",
            "severity": "critical"
        })
    if missing_dubs:
        issues.append({
            "issue": f"Missing required dub language(s) for {region}: {', '.join(missing_dubs)}",
            "severity": "high"
        })

    return issues


def run():
    requirements = load_requirements()
    df = load_metadata()
    region_requirements = requirements["region_requirements"]

    results = []
    for _, row in df.iterrows():
        issues = check_row(row, region_requirements)
        results.append({
            "content_id": row["content_id"],
            "title": row.get("title", "Unknown"),
            "region": row.get("release_region"),
            "issue_count": len(issues),
            "issues": issues,
            "status": "FAIL" if any(i["severity"] in ("critical", "high") for i in issues)
                      else ("WARN" if issues else "PASS")
        })

    return results


if __name__ == "__main__":
    for r in run():
        print(f"{r['content_id']} ({r['title']}, {r['region']}): {r['status']}")
        for issue in r["issues"]:
            print(f"    [{issue['severity'].upper()}] {issue['issue']}")
