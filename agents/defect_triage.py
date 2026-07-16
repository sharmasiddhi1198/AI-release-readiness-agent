"""
Defect Triage Agent
--------------------
The one genuinely "agentic" piece of this pipeline: instead of keyword
matching, this agent sends each defect ticket to Claude and asks it to
reason about severity and routing the way a human QA lead would --
weighing user-facing impact, scope (single scene vs whole title), and
whether it blocks launch.

Requires an ANTHROPIC_API_KEY environment variable to run for real.
Falls back to a clearly-labeled offline heuristic so the rest of the
pipeline (and the demo) still works without a live API key.
"""

import os
import json
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

TRIAGE_SYSTEM_PROMPT = """You are a QA release-triage assistant for a streaming platform.
For each defect ticket, decide:
1. severity: one of "critical" (blocks launch entirely), "high" (must fix before launch),
   "medium" (should fix soon, not launch-blocking), "low" (cosmetic/non-blocking)
2. routed_team: one of "Content Engineering On-Call", "Localization QA Lead",
   "Regional Content Ops", "Metadata Team (non-blocking)"
3. reasoning: one sentence explaining why

Respond ONLY with a JSON object: {"severity": "...", "routed_team": "...", "reasoning": "..."}
No markdown, no preamble."""


def load_tickets():
    return pd.read_csv(DATA_DIR / "defect_tickets.csv")


def _offline_heuristic(description: str, stage: str) -> dict:
    """
    Deterministic fallback used when no API key is present, so the demo
    and the rest of the pipeline remain runnable offline. Clearly labeled
    as a fallback -- the real agent reasoning happens via the Claude call
    in triage_ticket() below.
    """
    text = description.lower()
    if "fails to load" in text or "cuts out completely" in text:
        severity, team = "critical", "Content Engineering On-Call"
    elif "subtitle" in text or "dub" in text or "caption" in text:
        severity, team = "high", "Localization QA Lead"
    elif "typo" in text or "title card" in text:
        severity, team = "low", "Metadata Team (non-blocking)"
    else:
        severity, team = "medium", "Regional Content Ops"

    return {
        "severity": severity,
        "routed_team": team,
        "reasoning": f"[offline heuristic] Classified from keywords at stage '{stage}'."
    }


def triage_ticket(description: str, stage: str) -> dict:
    """Send a single ticket to Claude for reasoning-based triage."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _offline_heuristic(description, stage)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=TRIAGE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Ticket description: {description}\nDetected at stage: {stage}"
            }]
        )
        raw = message.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print("ANTHRPIC ERROR:",repr(e))
        result = _offline_heuristic(description, stage)
        result["reasoning"] += f" (API call failed: {e})"
        return result


def run():
    df = load_tickets()
    results = []
    for _, row in df.iterrows():
        triage = triage_ticket(row["description"], row["detected_stage"])
        results.append({
            "ticket_id": row["ticket_id"],
            "content_id": row["content_id"],
            "description": row["description"],
            **triage
        })
    return results


if __name__ == "__main__":
    for r in run():
        print(f"{r['ticket_id']} ({r['content_id']}): {r['severity'].upper()} -> {r['routed_team']}")
        print(f"    {r['reasoning']}")
