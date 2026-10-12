# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the app:**
```bash
streamlit run app.py
```

**Install dependencies:**
```bash
pip install -r requirements.txt
playwright install chromium
```

**Run all generated tests:**
```bash
pytest generated_tests/ -v --tb=short
```

**Run a single test file:**
```bash
pytest generated_tests/test_<name>.py -v
```

**Run with HTML report:**
```bash
pytest generated_tests/ -v --html=reports/report.html --self-contained-html
```

**Run with JSON report:**
```bash
pytest generated_tests/ -v --json-report --json-report-file=reports/test_results.json
```

**Environment setup:**
```bash
cp .env.example .env
# Set GROQ_API_KEY (free at console.groq.com) and optionally PLATFORM_PASSWORD
# Set BASE_URL to the app under test (localhost dev server or a live site) and,
# if it requires login, LOGIN_USERNAME/LOGIN_PASSWORD (+ LOGIN_*_SELECTOR if your
# login form isn't input[name="username"/"password"] + button[type="submit"]).
```

## Architecture

This is a monolithic Streamlit app (single `streamlit run app.py`) that implements an end-to-end AI-powered QA pipeline. The target app under test is configurable via `BASE_URL` in `.env` (point it at a localhost dev server or a live site, default `http://localhost:3000`) — the UI also ships with [SauceDemo](https://www.saucedemo.com) example requirements/data for demo purposes.

### Data flow

```
User Input → chains/ (LangChain LCEL) → services/ (DB + file I/O) → generated_tests/ (Playwright pytest files)
```

The full pipeline: **Requirements → Test Cases → Playwright Scripts → Execution → Failure Analysis → Self-Healing**

### Key layers

- **`core/`** — shared infrastructure: `config.py` (pydantic-settings from `.env`), `models.py` (SQLAlchemy ORM: Requirement → TestCase → Script → TestRun → Analysis → HealingAttempt), `database.py` (SQLite at `data/qa_platform.db`), `security.py` (input sanitization, path validation)
- **`chains/`** — LangChain LCEL chains (`prompt | llm | StrOutputParser()`). `chains/__init__.py::get_llm()` is the single provider factory — swap AI providers by changing `AI_PROVIDER` in `.env`. Includes `self_healing_chain.py`.
- **`services/`** — business logic that calls chains and writes to DB; services return plain `dict` (never ORM objects). Includes `healing_service.py`.
- **`pages/`** — Streamlit multipage files (`1_Dashboard.py` through `8_Self_Healing.py`); each checks `st.session_state["authenticated"]` at the top
- **`generated_tests/`** — AI-generated pytest+Playwright scripts land here; `conftest.py` provides `page` and `logged_in_page` fixtures
- **`self_healing_engine/`** — Self-healing: `dom_analyzer.py` (live DOM extraction), `locator_healer.py` (AI locator suggestions), `retry_engine.py` (full heal orchestration)
- **`qa_analytics_dashboard/`** — Analytics: `metrics_engine.py` (quality score, trend), `report_builder.py` (JSON/CSV export), `dashboard.py` (Streamlit wrapper)
- **`requirement_parser/`** — Requirement ingestion: `jira_loader.py` (Jira simulation + file loading), `requirement_schema.py` (Pydantic model)
- **`shared/`** — Central infrastructure: `logger.py`, `utils.py`, `config.py` (bridge to core.config)

### AI providers

Configured via `AI_PROVIDER` in `.env`. Supported values: `groq` (default, Llama 3.3 70B), `anthropic` (Claude), `google` (Gemini), `ollama` (local), `openai` (GPT, default model `gpt-4o-mini` via `OPENAI_MODEL`). Only the selected provider's package needs an API key.

### Security constraints

- `core/security.py::validate_script_path()` — enforces that executed scripts resolve inside `generated_tests/` (prevents path traversal)
- `core/security.py::validate_generated_script()` — AI-generated scripts must start with `import`/`from`
- `core/security.py::sanitize_input()` — strips prompt injection patterns and limits input to 5000 chars
- Execution (`services/execution_service.py`) accepts only a `script_id`; the path is fetched from DB, never taken from user input

### Module directories (importable Python packages)

New modules use underscore names for Python imports; hyphenated directories mirror the same structure for display:

| Package | Purpose |
|---|---|
| `self_healing_engine/` | DOM analysis + AI locator healing |
| `test_execution_engine/` | Batch execution + JSON log collection |
| `requirement_parser/` | Jira simulation + file-based ingestion |
| `qa_analytics_dashboard/` | Metrics engine + report builder |
| `ai_failure_analyzer/` | Failure parsing + root cause classification |
| `shared/` | Logger, utils, config bridge |

### Supporting directories (not imported by app)

- `ai-testcase-generator/` — testcase_model, prompt_templates, generator wrappers
- `automation-script-generator/` — selector_strategy, test_template, playwright_generator wrappers
- `sample-app/` — SauceDemo reference documentation
- `test-data/` — sample requirements, test cases, execution logs
- `documentation/` — architecture.md, demo-guide.md, ai-prompts.md
- `ci_cd/` — GitHub Actions pipeline
