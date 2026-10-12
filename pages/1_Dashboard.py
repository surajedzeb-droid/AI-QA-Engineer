import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from core.database import init_db
from services.requirement_service import get_all_requirements
from services.testcase_service import get_all_test_cases
from services.script_service import get_all_scripts
from services.execution_service import get_run_summary, get_all_runs

init_db()

if not st.session_state.get("authenticated"):
    st.warning("Please login first.")
    st.stop()

st.title("Dashboard")
st.markdown("AI Quality Engineering Platform — Test Coverage")

reqs = get_all_requirements()
tcs = get_all_test_cases()
scripts = get_all_scripts()
summary = get_run_summary()
runs = get_all_runs()

# ── Quality Score ──────────────────────────────────────────────────────────
try:
    from services.healing_service import get_healing_stats
    from qa_analytics_dashboard.metrics_engine import MetricsEngine

    healing_stats = get_healing_stats()
    healing_list = [{"status": "healed"}] * healing_stats["healed"] + [{"status": "failed"}] * healing_stats["failed"]

    # analyses proxy: just pass empty list for coverage calc (no heavy DB query needed here)
    quality_score = MetricsEngine().compute_quality_score(runs, [], healing_list)
except Exception:
    quality_score = round(summary["pass_rate"] * 0.5, 1)
    healing_stats = {"total": 0, "healed": 0, "success_rate": 0.0}

# ── Top Metrics ────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Quality Score", f"{quality_score}/100")
col2.metric("Requirements", len(reqs))
col3.metric("Test Cases", len(tcs))
col4.metric("Scripts", len(scripts))
col5.metric("Pass Rate", f"{summary['pass_rate']}%")

st.divider()

# ── Charts Row 1 ───────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Test Runs by Status")
    if summary["total"] > 0:
        fig = px.pie(
            values=[summary["passed"], summary["failed"], summary["error"]],
            names=["Passed", "Failed", "Error"],
            color_discrete_map={"Passed": "#22c55e", "Failed": "#ef4444", "Error": "#f97316"},
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No test runs yet. Execute scripts to see results.")

with col_right:
    st.subheader("Requirements by Feature")
    if reqs:
        feature_counts = {}
        for r in reqs:
            feature_counts[r["feature"]] = feature_counts.get(r["feature"], 0) + 1
        fig = px.bar(
            x=list(feature_counts.keys()),
            y=list(feature_counts.values()),
            labels={"x": "Feature", "y": "Count"},
            color=list(feature_counts.keys()),
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No requirements yet. Add requirements to see breakdown.")

# ── Execution Trend ────────────────────────────────────────────────────────
st.subheader("Execution Trend")
if runs:
    try:
        from qa_analytics_dashboard.metrics_engine import MetricsEngine
        trend_df = MetricsEngine().get_execution_trend(runs)
        if not trend_df.empty:
            fig = px.line(
                trend_df,
                x="date",
                y=["passed", "failed", "error"],
                color_discrete_map={"passed": "#22c55e", "failed": "#ef4444", "error": "#f97316"},
                labels={"value": "Runs", "variable": "Status", "date": "Date"},
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough date data for trend chart.")
    except Exception:
        st.info("Trend chart unavailable.")
else:
    st.info("No test runs yet.")

# ── Self-Healing Mini Section ──────────────────────────────────────────────
st.subheader("Self-Healing Summary")
h_col1, h_col2, h_col3 = st.columns(3)
h_col1.metric("Total Healing Attempts", healing_stats["total"])
h_col2.metric("Successfully Healed", healing_stats["healed"])
h_col3.metric("Healing Success Rate", f"{healing_stats['success_rate']}%")

# ── Recent Test Runs ───────────────────────────────────────────────────────
st.subheader("Recent Test Runs")
if runs:
    df = pd.DataFrame(runs[:10])
    display_cols = ["id", "test_name", "feature", "status", "duration_seconds", "started_at"]
    df = df[[c for c in display_cols if c in df.columns]]
    df.columns = ["ID", "Test Name", "Feature", "Status", "Duration (s)", "Started At"][:len(df.columns)]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No test runs yet.")
