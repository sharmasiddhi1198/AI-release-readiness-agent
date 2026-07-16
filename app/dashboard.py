"""
Release Readiness Agent - Dashboard
-------------------------------------
Run with: streamlit run app/dashboard.py
(run from the project root so the `agents` package import resolves)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from agents import orchestrator

st.set_page_config(page_title="Release Readiness Agent", layout="wide")

STATUS_COLORS = {
    "GO": "🟢",
    "GO WITH CONDITIONS": "🟡",
    "NO-GO": "🔴",
    "PASS": "🟢",
    "WARN": "🟡",
    "FAIL": "🔴",
}

st.title("🎬 Release Readiness Agent")
st.caption(
    "Agentic pre-launch QA: metadata validation, localization coverage, and "
    "defect triage combined into a single Go / No-Go recommendation."
)

with st.sidebar:
    st.header("About this pipeline")
    st.markdown(
        "**3 agents + orchestrator:**\n\n"
        "1. Metadata Validator (rules-based)\n"
        "2. Localization Checker (rules-based)\n"
        "3. Defect Triage (LLM-reasoned severity + routing)\n"
        "4. Orchestrator (aggregates + writes Go/No-Go justification)\n\n"
        "If no `ANTHROPIC_API_KEY` is set, the triage and summary steps fall "
        "back to a labeled offline heuristic so the demo still runs."
    )

if st.button("▶ Run Readiness Check", type="primary"):
    with st.spinner("Running agents..."):
        st.session_state["report"] = orchestrator.run()

report = st.session_state.get("report")

if report:
    go_count = sum(1 for r in report if r["overall_status"] == "GO")
    conditional_count = sum(1 for r in report if r["overall_status"] == "GO WITH CONDITIONS")
    nogo_count = sum(1 for r in report if r["overall_status"] == "NO-GO")

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Go", go_count)
    col2.metric("🟡 Go with Conditions", conditional_count)
    col3.metric("🔴 No-Go", nogo_count)

    st.divider()

    for r in report:
        icon = STATUS_COLORS.get(r["overall_status"], "")
        with st.expander(f"{icon} {r['title']} ({r['content_id']}) — {r['overall_status']}"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Metadata:** {STATUS_COLORS.get(r['metadata_status'])} {r['metadata_status']}")
            c2.write(f"**Localization:** {STATUS_COLORS.get(r['localization_status'])} {r['localization_status']}")
            c3.write(f"**Critical/High Defects:** {r['critical_or_high_defects']} of {r['defect_count']}")

            st.markdown(f"**Release Manager Summary:**\n\n> {r['summary']}")

            if r["all_issues"]:
                st.markdown("**All flagged issues:**")
                for issue in r["all_issues"]:
                    st.markdown(f"- {issue}")
else:
    st.info("Click **Run Readiness Check** to evaluate all titles in the launch queue.")
