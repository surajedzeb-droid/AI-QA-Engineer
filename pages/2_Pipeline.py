import traceback
import streamlit as st
from core.config import settings
from core.database import init_db
from services.requirement_service import get_all_requirements, create_requirements_from_text
from services.testcase_service import create_test_cases_for_requirement, get_test_cases_by_requirement
from services.script_service import create_script_for_test_case, get_all_scripts
from services.execution_service import execute_script
from services.site_service import analyze_target_site, get_sitemap_pages

init_db()

if not st.session_state.get("authenticated"):
    st.warning("Please login first.")
    st.stop()

st.title("AI Pipeline")
st.markdown("Run the full AI pipeline: Requirements → Test Cases → Scripts → Execution")

st.caption(f"Target app: `{settings.BASE_URL}` — change BASE_URL in .env to point at localhost or a live site.")


def _apply_suggestion(feature_name: str, description: str):
    st.session_state["pipeline_feature"] = feature_name
    st.session_state["pipeline_req_text"] = description


with st.expander("🔍 Analyze Target Site (suggest features from what's actually on the page)", expanded=False):
    # Re-fetch automatically whenever BASE_URL changes, so this never shows a stale
    # sitemap left over from a previously targeted site.
    if st.session_state.get("sitemap_pages_url") != settings.BASE_URL:
        with st.spinner(f"Fetching {settings.BASE_URL.rstrip('/')}/sitemap.xml ..."):
            st.session_state["sitemap_pages"] = get_sitemap_pages(settings.BASE_URL)
            st.session_state["sitemap_pages_url"] = settings.BASE_URL
        # Target changed — drop any leftover analysis from the previous site.
        st.session_state.pop("site_analysis", None)
        st.session_state.pop("site_analysis_url", None)

    if st.button("Re-fetch Sitemap"):
        with st.spinner(f"Fetching {settings.BASE_URL.rstrip('/')}/sitemap.xml ..."):
            st.session_state["sitemap_pages"] = get_sitemap_pages(settings.BASE_URL)
            st.session_state["sitemap_pages_url"] = settings.BASE_URL

    sitemap_pages = st.session_state.get("sitemap_pages", [])
    page_options = sitemap_pages if sitemap_pages else [settings.BASE_URL]
    if not sitemap_pages:
        st.caption(f"No sitemap.xml found at {settings.BASE_URL.rstrip('/')}/sitemap.xml — falling back to BASE_URL only.")
    else:
        st.caption(f"Found {len(sitemap_pages)} page(s) in sitemap.xml for `{settings.BASE_URL}`.")

    page_to_analyze = st.selectbox("Page to analyze", page_options)

    if st.button("Analyze This Page"):
        with st.spinner(f"Crawling {page_to_analyze} and asking AI for testable features..."):
            result = analyze_target_site(page_to_analyze)
            st.session_state["site_analysis"] = result
            st.session_state["site_analysis_url"] = page_to_analyze

    analysis = st.session_state.get("site_analysis")
    if analysis:
        analyzed_url = st.session_state.get("site_analysis_url", settings.BASE_URL)
        if analysis["error"]:
            st.error(f"Could not analyze {analyzed_url}: {analysis['error']}")
        elif not analysis["suggestions"]:
            st.warning("Page was reached but no feature suggestions came back. Try again or enter requirements manually below.")
        else:
            st.caption(f"Based on {analyzed_url} — \"{analysis['summary'].get('title', '')}\"")
            for s in analysis["suggestions"]:
                col1, col2 = st.columns([5, 1])
                col1.markdown(f"**{s.get('feature', 'Untitled')}** — {s.get('description', '')}")
                col2.button(
                    "Use",
                    key=f"use_{s.get('feature', '')}_{hash(s.get('description', ''))}",
                    on_click=_apply_suggestion,
                    args=(s.get("feature", ""), s.get("description", "")),
                )

feature = st.text_input(
    "Feature name",
    placeholder="e.g. Login, Search, Checkout, Password Reset",
    key="pipeline_feature",
)
custom_req_text = st.text_area(
    "Describe the feature/requirement to test",
    placeholder="e.g. Users must be able to reset their password via the 'Forgot password' link on /login.",
    height=120,
    key="pipeline_req_text",
)

if st.button("Run Full Pipeline", type="primary"):
    req_text = custom_req_text.strip()
    if not req_text:
        st.warning("Please describe the feature/requirement to test first.")
        st.stop()
    if not feature.strip():
        feature = "Custom"

    log_container = st.container()

    with log_container:
        # Step 1: Parse Requirements
        with st.status(f"Step 1/5: Parsing requirements for {feature}...", expanded=True) as status:
            try:
                reqs = create_requirements_from_text(req_text)
                status.update(label=f"Step 1/5: Requirements parsed ({len(reqs)} found)", state="complete")
                st.write(f"Created {len(reqs)} requirement(s)")
            except Exception as e:
                status.update(label="Step 1/5: Failed to parse requirements", state="error")
                st.error(f"Requirement parsing failed: {type(e).__name__}")
                st.code(traceback.format_exc())
                st.stop()

        req = reqs[0] if reqs else None
        if not req:
            st.error("No requirements generated.")
            st.stop()

        # Step 2: Generate Test Cases
        with st.status("Step 2/5: Generating test cases...", expanded=True) as status:
            try:
                tcs = create_test_cases_for_requirement(req)
                status.update(label=f"Step 2/5: Test cases generated ({len(tcs)} found)", state="complete")
                st.write(f"Created {len(tcs)} test case(s)")
            except Exception as e:
                status.update(label="Step 2/5: Failed to generate test cases", state="error")
                st.error(f"Test case generation failed: {type(e).__name__}")
                st.code(traceback.format_exc())
                st.stop()

        tc = tcs[0] if tcs else None
        if not tc:
            st.error("No test cases generated.")
            st.stop()

        # Step 3: Generate Script
        with st.status("Step 3/5: Generating Playwright script...", expanded=True) as status:
            try:
                script = create_script_for_test_case(req, tc)
                status.update(label="Step 3/5: Script generated", state="complete")
                st.write(f"Script saved: {script['script_path']}")
            except Exception as e:
                status.update(label="Step 3/5: Failed to generate script", state="error")
                st.error(f"Script generation failed: {type(e).__name__}")
                st.code(traceback.format_exc())
                st.stop()

        # Step 4: Execute Script
        with st.status("Step 4/5: Executing test...", expanded=True) as status:
            try:
                run = execute_script(script["id"])
                state = "complete" if run["status"] == "passed" else "error"
                status.update(label=f"Step 4/5: Execution {run['status']} ({run['duration_seconds']}s)", state=state)
                st.write(f"Status: **{run['status']}**")
                if run.get("output"):
                    st.code(run["output"][:2000], language="text")
            except Exception as e:
                status.update(label="Step 4/5: Execution error", state="error")
                st.error(f"Execution failed: {type(e).__name__}")
                st.code(traceback.format_exc())
                run = None

        # Step 5: Summary
        with st.status("Step 5/5: Pipeline complete", expanded=False) as status:
            status.update(label="Step 5/5: Pipeline complete", state="complete")

    st.success(f"Pipeline finished for **{feature}** feature!")
    st.markdown(f"""
**Results:**
- Requirements: {len(reqs)}
- Test Cases: {len(tcs)}
- Script: `{script['title']}`
- Execution: {run['status'] if run else 'N/A'}
""")

    if run and run["status"] != "passed":
        st.info("Go to **Failure Analysis** page to analyze this test failure.")
