try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass  # truststore not installed; SSL will use certifi bundle

import streamlit as st
from core.config import settings
from core.database import init_db

st.set_page_config(
    page_title="AI Quality Engineering Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


def login_page():
    st.title("AI Quality Engineering Platform")
    st.markdown("**Powered by LangChain + Playwright + Streamlit**")
    st.markdown(f"Target Application: `{settings.BASE_URL}` _(set `BASE_URL` in .env to point at localhost or a live site)_")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", type="primary", use_container_width=True):
            if username == settings.PLATFORM_USERNAME and password == settings.PLATFORM_PASSWORD:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid credentials. Check PLATFORM_USERNAME and PLATFORM_PASSWORD in .env")

        st.caption("Default credentials are set in .env file (PLATFORM_USERNAME / PLATFORM_PASSWORD)")


def main():
    if not st.session_state.get("authenticated"):
        login_page()
        return

    with st.sidebar:
        st.markdown(f"Logged in as **{st.session_state.get('username', 'admin')}**")
        st.caption(f"AI Provider: `{settings.AI_PROVIDER}`")
        st.caption(f"Target App: `{settings.BASE_URL}`")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    st.title("AI Quality Engineering Platform")
    st.markdown("""
Welcome! Use the sidebar to navigate between pages:

| Page | Description |
|------|-------------|
| **Dashboard** | KPIs, charts, recent test runs |
| **Pipeline** | Run the full AI pipeline end-to-end |
| **Requirements** | Parse requirements with AI |
| **Test Cases** | Generate test cases from requirements |
| **Scripts** | Generate Playwright automation scripts |
| **Execution** | Execute tests and view results |
| **Failure Analysis** | AI-powered root cause analysis |
| **Self-Healing** | Auto-heal broken test locators with AI |
""")

    st.info("Select a page from the sidebar to get started.")


if __name__ == "__main__":
    main()
