# Release Readiness Agent

An agentic pre-launch QA system for streaming content. Combines rule-based
validation with LLM-reasoned defect triage to produce a single, justified
**Go / No-Go / Go-with-Conditions** recommendation per title — the kind of
release gate a content ops or QA team runs before a title goes live.

Built to bring together a QA engineering background (7+ years, Amazon BI &
Analytics) with hands-on agentic AI development.

## Why this exists

Pre-launch content review usually means checking metadata completeness,
localization coverage (subtitles/dubs per region), and outstanding QA
defects — separately, by different people, without a single view of
"are we actually ready to launch." This project automates that gate and
adds an LLM reasoning layer that explains *why*, the way a release manager
would in a sign-off meeting.

## Architecture

```
┌─────────────────────┐   ┌──────────────────────┐   ┌───────────────────┐
│ Metadata Validator   │   │ Localization Checker │   │ Defect Triage      │
│ (rules-based)        │   │ (rules-based)         │   │ (LLM-reasoned)      │
└──────────┬───────────┘   └───────────┬──────────┘   └─────────┬──────────┘
           │                           │                        │
           └───────────────┬───────────┴────────────┬───────────┘
                            ▼                        
                  ┌────────────────────┐
                  │    Orchestrator     │  → aggregates findings per title
                  │ (LLM justification) │  → writes Go/No-Go summary
                  └──────────┬──────────┘
                             ▼
                   Streamlit Dashboard
```

1. **Metadata Validator** — checks required fields (rating, runtime, release
   date, artwork status, etc.) are present and well-formed.
2. **Localization Checker** — verifies subtitle/dub language coverage against
   per-region launch requirements (e.g. a JP release needs JA subs + dub).
3. **Defect Triage** — sends each open QA ticket to Claude, which reasons
   about severity (critical/high/medium/low) and routes it to the right team,
   rather than relying on brittle keyword matching.
4. **Orchestrator** — merges all three signals per title, computes an overall
   status, and asks Claude to write a short human-readable justification.

If `ANTHROPIC_API_KEY` isn't set, the LLM-backed steps fall back to a clearly
labeled offline heuristic so the whole pipeline still runs end-to-end for
demo purposes.

## Running it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here   # optional — falls back to heuristic without it

# Run the pipeline from the command line:
python3 -m agents.orchestrator

# Or launch the interactive dashboard:
streamlit run app/dashboard.py
```

## Project structure

```
release-readiness-agent/
├── data/
│   ├── content_metadata.csv      # mock titles queued for launch
│   ├── defect_tickets.csv        # mock QA bug tickets
│   └── launch_requirements.json  # per-region localization rules
├── agents/
│   ├── metadata_validator.py
│   ├── localization_checker.py
│   ├── defect_triage.py
│   └── orchestrator.py
├── app/
│   └── dashboard.py               # Streamlit UI
└── requirements.txt
```

## Sample output

A title missing its Portuguese dub for a Brazil launch, with an open
critical defect on the same dub track, gets flagged as **NO-GO** with a
plain-English explanation — rather than three disconnected reports someone
has to manually cross-reference before a launch call.

## Possible extensions

- Swap the mock CSVs for a real content catalog API
- Add a Slack/email notification agent that posts the Go/No-Go summary
  automatically to a release channel
- Add historical tracking so recurring defect patterns surface over time
