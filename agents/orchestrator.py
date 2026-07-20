"""
Orchestrator
------------
Runs all three agents, aggregates their findings per content_id, and
produces a final Go/No-Go readiness report per title. Calls Claude once
more (if a key is available) to write a short human-readable justification
in the voice of a release manager -- this is the layer that turns three
separate checks into one coherent recommendation.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from agents import metadata_validator, localization_checker, defect_triage

DATA_DIR = Path(__file__).parent.parent / "data"

SUMMARY_SYSTEM_PROMPT = """You are a release manager writing a brief Go/No-Go
justification for a content title about to launch on a streaming platform.
You will be given structured findings from metadata validation, localization
checks, and defect triage. Write 2-3 sentences: state the decision (GO / NO-GO
/ GO WITH CONDITIONS), then justify it referencing the most important issue(s).
Be direct and specific. No preamble, no markdown."""


def _offline_summary(content_id, title, status, all_issues):
    if status == "FAIL":
        top = all_issues[0] if all_issues else "unresolved blocking issues"
        return (f"[offline heuristic] NO-GO for '{title}'. Blocking issue found: {top}. "
                f"Recommend holding launch until Content Engineering and Localization QA sign off.")
    elif status == "WARN":
        return (f"[offline heuristic] GO WITH CONDITIONS for '{title}'. Non-blocking issues "
                f"remain open and should be tracked post-launch.")
    else:
        return f"[offline heuristic] GO for '{title}'. No blocking issues found across all checks."


def _llm_summary(content_id, title, status, all_issues):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _offline_summary(content_id, title, status, all_issues)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        payload = {
            "content_id": content_id,
            "title": title,
            "computed_status": status,
            "issues_found": all_issues
        }
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print("SUMMARY API ERROR:",repr(e))
        return _offline_summary(content_id, title, status, all_issues) + f" (API call failed: {e})"


def run(input_data=None):
    metadata_results = {
    r["content_id"]: r
    for r in metadata_validator.run(input_data)
}
    localization_results = {r["content_id"]: r for r in localization_checker.run()}
    triage_results = defect_triage.run()

    # Group defect tickets by content_id
    triage_by_content = {}
    for t in triage_results:
        triage_by_content.setdefault(t["content_id"], []).append(t)

    all_content_ids = set(metadata_results) | set(localization_results) | set(triage_by_content)

    report = []
    for cid in sorted(all_content_ids):
        meta = metadata_results.get(cid, {"status": "PASS", "issues": []})
        loc = localization_results.get(cid, {"status": "PASS", "issues": []})
        tickets = triage_by_content.get(cid, [])

        title = meta.get("title") or loc.get("title") or cid

        all_issue_descriptions = (
            [i["issue"] for i in meta.get("issues", [])] +
            [i["issue"] for i in loc.get("issues", [])] +
            [f"Defect {t['ticket_id']}: {t['description']} (severity: {t['severity']})"
             for t in tickets if t["severity"] in ("critical", "high")]
        )

        statuses = [meta["status"], loc["status"]]
        has_blocking_defect = any(t["severity"] == "critical" for t in tickets)
        if "FAIL" in statuses or has_blocking_defect:
            overall_status = "NO-GO"
        elif "WARN" in statuses or any(t["severity"] == "high" for t in tickets):
            overall_status = "GO WITH CONDITIONS"
        else:
            overall_status = "GO"

        # map to internal FAIL/WARN/PASS vocabulary for the summary helper
        internal_status = {"NO-GO": "FAIL", "GO WITH CONDITIONS": "WARN", "GO": "PASS"}[overall_status]
        summary = _llm_summary(cid, title, internal_status, all_issue_descriptions)

        report.append({
            "content_id": cid,
            "title": title,
            "overall_status": overall_status,
            "metadata_status": meta["status"],
            "localization_status": loc["status"],
            "defect_count": len(tickets),
            "critical_or_high_defects": sum(1 for t in tickets if t["severity"] in ("critical", "high")),
            "summary": summary,
            "all_issues": all_issue_descriptions
        })

    return report


if __name__ == "__main__":
    results = run()
    print(json.dumps(results, indent=2))
