import traceback
import streamlit as st
from core.database import init_db, get_session
from core.models import Analysis
from services.execution_service import get_all_runs, get_run_by_id
from services.script_service import get_script_by_id
from chains.failure_analyzer_chain import analyze_failure
from self_healing_engine.dom_analyzer import extract_locators_safe, summarize_dom_for_context

init_db()

if not st.session_state.get("authenticated"):
    st.warning("Please login first.")
    st.stop()

st.title("Failure Analysis")
st.markdown("AI-powered root cause analysis for failed tests.")

runs = get_all_runs()
failed_runs = [r for r in runs if r["status"] in ("failed", "error")]

if not failed_runs:
    st.info("No failed test runs. Execute some tests first — failures will appear here for analysis.")
else:
    st.subheader("Analyze a Failure")
    run_options = {
        f"#{r['id']} — {r['test_name']} [{r['status']}]": r
        for r in failed_runs
    }
    selected_label = st.selectbox("Select Failed Run", list(run_options.keys()))
    selected_run = run_options[selected_label]

    if st.button("Analyze with AI", type="primary"):
        script = get_script_by_id(selected_run["script_id"]) if selected_run.get("script_id") else None
        script_content = script["script_content"] if script else ""
        failure_output = (selected_run.get("output") or "") + (selected_run.get("error_message") or "")

        with st.spinner("Analyzing failure with AI..."):
            try:
                dom_context_summary = ""
                try:
                    dom_context = extract_locators_safe()
                    dom_context_summary = summarize_dom_for_context(
                        dom_context, selected_run["test_name"] + " " + script_content[:1000]
                    )
                except Exception:
                    pass  # Proceed without live DOM grounding rather than fail the whole analysis.

                result = analyze_failure(
                    test_name=selected_run["test_name"],
                    failure_output=failure_output,
                    script_content=script_content,
                    dom_context=dom_context_summary,
                )

                db = get_session()
                try:
                    analysis = Analysis(
                        run_id=selected_run["id"],
                        test_name=selected_run["test_name"],
                        failure_output=failure_output[:5000],
                        root_cause=result.get("root_cause", ""),
                        failure_category=result.get("failure_category", "ScriptError"),
                        suggested_fix=result.get("suggested_fix", ""),
                        fixed_script=result.get("fixed_script"),
                        severity=result.get("severity", "Medium"),
                    )
                    db.add(analysis)
                    db.commit()
                finally:
                    db.close()

                st.success("Analysis complete!")

                severity_colors = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
                severity = result.get("severity", "Medium")
                col1, col2 = st.columns(2)
                col1.metric("Severity", f"{severity_colors.get(severity, '')} {severity}")
                col2.metric("Category", result.get("failure_category", "Unknown"))

                with st.expander("Root Cause", expanded=True):
                    st.write(result.get("root_cause", "N/A"))

                with st.expander("Suggested Fix", expanded=True):
                    st.write(result.get("suggested_fix", "N/A"))

                if result.get("fixed_script"):
                    with st.expander("Fixed Script"):
                        st.code(result["fixed_script"], language="python")
                        st.download_button(
                            "Download Fixed Script",
                            data=result["fixed_script"],
                            file_name=f"fixed_{selected_run['test_name']}.py",
                            mime="text/x-python",
                        )

            except Exception as e:
                st.error("Analysis failed. Check your AI provider configuration.")
                with st.expander("Error details", expanded=True):
                    st.code(traceback.format_exc())

st.divider()

st.subheader("Previous Analyses")
db = get_session()
try:
    analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).all()
finally:
    db.close()

if not analyses:
    st.info("No analyses yet.")
else:
    for a in analyses:
        severity_colors = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
        icon = severity_colors.get(a.severity, "⚪")
        with st.expander(f"{icon} [{a.severity}] {a.test_name} — {a.failure_category}"):
            st.markdown(f"**Root Cause:** {a.root_cause}")
            st.markdown(f"**Suggested Fix:** {a.suggested_fix}")
            if a.fixed_script:
                st.code(a.fixed_script, language="python")
