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
import pandas as pd
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
st.divider()

st.subheader("📋 Release Information")

with st.form("release_form"):

    title = st.text_input("Content Title")

    content_id = st.text_input("Content ID")

    release_region = st.selectbox(
        "Release Region",
        ["US", "India", "EU", "Japan", "Global"]
    )

    release_date = st.date_input("Release Date")

    runtime = st.number_input(
        "Runtime (minutes)",
        min_value=1,
        value=90
    )

    content_rating = st.selectbox(
        "Content Rating",
        ["G", "PG", "PG-13", "R", "TV-14", "TV-MA"]
    )

    artwork_status = st.selectbox(
        "Artwork Status",
        ["approved", "pending", "missing"]
    )

    subtitle_languages = st.multiselect(
        "Subtitle Languages",
        ["english", "hindi", "spanish", "french", "japanese"]
    )

    dub_languages = st.multiselect(
        "Dub Languages",
        ["english", "hindi", "spanish", "french", "japanese"]
    )

    submitted = st.form_submit_button("Continue")
    if submitted:
            if not title.strip() or not content_id.strip():
             st.error("Please enter both Content Title and Content ID.")
             st.session_state["release_saved"] = False
            else:
             st.session_state["release_input"] = {
                "title": title.strip(),
                "content_id": content_id.strip(),
                "release_region": release_region,
                "release_date": str(release_date),
                "runtime": runtime,
                "content_rating": content_rating,
                "artwork_status": artwork_status,
                "subtitle_languages": subtitle_languages,
                "dub_languages": dub_languages,
                    }

             st.session_state["release_saved"] = True

if st.session_state.get("release_saved", False):
    st.success("✅ Release information saved successfully!") 

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
        st.session_state["report"] = orchestrator.run(
    st.session_state.get("release_input")
)

raw_report = st.session_state.get("report")

if isinstance(raw_report, list):
    report = raw_report
elif isinstance(raw_report, dict):
    report = raw_report.get("report") or raw_report.get("results") or []
else:
    report = []

if report:
    go_count = sum(1 for r in report if r["overall_status"] == "GO")
    conditional_count = sum(1 for r in report if r["overall_status"] == "GO WITH CONDITIONS")
    nogo_count = sum(1 for r in report if r["overall_status"] == "NO-GO")

    total_titles = go_count + conditional_count + nogo_count

    titles_column, go_column, conditional_column, nogo_column = st.columns(4)

    titles_column.metric(
            "🎬 Titles",
            total_titles,
            help="Total titles evaluated"
        )

    go_column.metric(
            "🟢 GO",
            go_count
        )

    conditional_column.metric(
            "🟡 Conditional",
            conditional_count
        )

    nogo_column.metric(
            "🔴 NO-GO",
            nogo_count
        )

    st.divider()
    st.subheader("Release Status Distribution")

    status_data = pd.DataFrame(
        {
            "Status": ["GO", "GO WITH CONDITIONS", "NO-GO"],
            "Count": [go_count, conditional_count, nogo_count],
        }
    )

    st.bar_chart(
        status_data,
        x="Status",
        y="Count",
        use_container_width=True
    )

st.divider()
st.subheader("Executive Release Dashboard")
st.caption(
        "Aggregated recommendations produced by metadata validation, localization analysis, and AI-assisted defect triage."
    )
status_filter = st.selectbox(
    "Filter by Release Status",
    ["All", "GO", "GO WITH CONDITIONS", "NO-GO"]
)

if status_filter == "All":
    filtered_report = report
else:
    filtered_report = [
        r for r in report
        if r["overall_status"] == status_filter
    ]

download_data = pd.DataFrame(
[
{
"Content ID": r["content_id"],
"Title": r["title"],
"Overall Status": r["overall_status"],
"Metadata Status": r["metadata_status"],
"Localization Status": r["localization_status"],
"Critical or High Defects": r["critical_or_high_defects"],
"Summary": r["summary"],
}
for r in filtered_report
]
)

csv_data = download_data.to_csv(index=False).encode("utf-8")

st.download_button(
label="⬇️ Download Executive Report",
data=csv_data,
file_name="release_readiness_report.csv",
mime="text/csv",
)

for r in filtered_report:
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
