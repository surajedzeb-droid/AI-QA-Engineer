import traceback
import streamlit as st
from core.database import init_db
from services.requirement_service import (
    get_all_requirements,
    create_requirements_from_text,
    seed_default_requirements,
)

init_db()

if not st.session_state.get("authenticated"):
    st.warning("Please login first.")
    st.stop()

st.title("Requirements")
st.markdown("Parse natural language requirements into structured QA requirements using AI.")

with st.expander("AI Connection Test"):
    if st.button("Test AI Connection"):
        try:
            from chains import get_llm
            llm = get_llm()
            response = llm.invoke("Say 'OK' in one word.")
            st.success(f"Connected! Response: {response.content}")
        except Exception:
            st.error("Connection failed")
            st.code(traceback.format_exc())

# ── Input Tabs ─────────────────────────────────────────────────────────────
tab_text, tab_file, tab_jira = st.tabs(["Manual Text", "File Upload", "Jira Simulation"])

with tab_text:
    st.markdown("Enter requirement text manually and parse it with AI.")
    col1, col2 = st.columns([3, 1])
    with col1:
        user_input = st.text_area(
            "Enter requirements text",
            placeholder="e.g. Test login with valid and invalid credentials.",
            height=150,
            max_chars=5000,
            key="manual_input",
        )
    with col2:
        st.markdown("&nbsp;")
        parse_btn = st.button("Parse with AI", type="primary", use_container_width=True)
        seed_btn = st.button("Seed Example Requirements (SauceDemo demo)", use_container_width=True)

    if parse_btn:
        if not user_input.strip():
            st.warning("Please enter some requirement text first.")
        else:
            with st.spinner("Parsing requirements with AI..."):
                try:
                    new_reqs = create_requirements_from_text(user_input)
                    st.success(f"Created {len(new_reqs)} requirement(s)!")
                except Exception:
                    st.error("Failed to parse requirements. Check your AI provider configuration.")
                    with st.expander("Error details", expanded=True):
                        st.code(traceback.format_exc())

    if seed_btn:
        with st.spinner("Seeding example SauceDemo requirements..."):
            try:
                seeded = seed_default_requirements()
                st.success(f"Seeded {len(seeded)} default requirement(s)!")
            except Exception:
                st.error("Failed to seed requirements.")
                with st.expander("Error details", expanded=True):
                    st.code(traceback.format_exc())

with tab_file:
    st.markdown("Upload a `.txt` file where each line is a separate requirement.")
    uploaded = st.file_uploader("Upload requirements file", type=["txt", "md"])

    if uploaded is not None:
        content = uploaded.read().decode("utf-8")
        st.text_area("File preview", content[:1000], height=120, disabled=True)

        if st.button("Parse File with AI", type="primary"):
            from requirement_parser.jira_loader import JiraLoader
            loader = JiraLoader()
            items = loader.load_from_file(content)

            if not items:
                st.warning("No non-empty lines found in the file.")
            else:
                with st.spinner(f"Parsing {len(items)} line(s) with AI..."):
                    created = []
                    errors = []
                    for item in items:
                        try:
                            new_reqs = create_requirements_from_text(item["description"])
                            created.extend(new_reqs)
                        except Exception as e:
                            errors.append(str(e))
                    if created:
                        st.success(f"Created {len(created)} requirement(s) from file!")
                    if errors:
                        st.warning(f"{len(errors)} line(s) failed to parse.")

with tab_jira:
    st.markdown("Simulate loading requirements from a Jira project sprint (built-in demo data — your own Jira stories can be pasted via the Manual Text tab).")

    from requirement_parser.jira_loader import JiraLoader
    loader = JiraLoader()
    projects = loader.available_projects()

    selected_project = st.selectbox("Select Jira Project / Sprint", projects)

    if selected_project:
        stories = loader.simulate_jira_stories(selected_project)
        st.markdown(f"**{len(stories)} stories** loaded from *{selected_project}*")

        with st.expander("Preview stories"):
            for s in stories:
                st.markdown(f"- **[{s['feature']}]** {s['title']} — _{s['priority']}_")

        if st.button("Import & Parse Stories with AI", type="primary"):
            with st.spinner(f"Parsing {len(stories)} Jira stories with AI..."):
                created = []
                errors = []
                for story in stories:
                    try:
                        text = f"{story['title']}\n{story['description']}\nAcceptance Criteria: {story['acceptance_criteria']}"
                        new_reqs = create_requirements_from_text(text)
                        created.extend(new_reqs)
                    except Exception as e:
                        errors.append(str(e))
                if created:
                    st.success(f"Imported {len(created)} requirement(s) from {selected_project}!")
                if errors:
                    st.warning(f"{len(errors)} stories failed to parse.")

# ── Requirements List ──────────────────────────────────────────────────────
st.divider()
reqs = get_all_requirements()
st.subheader(f"All Requirements ({len(reqs)})")

if not reqs:
    st.info("No requirements yet. Enter your own requirements above (Manual Text / File Upload), or click 'Seed Example Requirements' to try a SauceDemo demo set.")
else:
    feature_filter = st.selectbox(
        "Filter by Feature",
        ["All"] + sorted(set(r["feature"] for r in reqs)),
    )

    filtered = reqs if feature_filter == "All" else [r for r in reqs if r["feature"] == feature_filter]

    for req in filtered:
        priority_colors = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
        icon = priority_colors.get(req["priority"], "⚪")
        with st.expander(f"{icon} [{req['feature']}] {req['title']}"):
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**Priority:** {req['priority']}")
            col_b.markdown(f"**Feature:** {req['feature']}")
            col_c.markdown(f"**ID:** #{req['id']}")
            st.markdown(f"**Description:** {req['description']}")
            st.markdown(f"**Acceptance Criteria:**\n{req['acceptance_criteria']}")
            st.markdown(f"**Test Types:** {req['test_types']}")
