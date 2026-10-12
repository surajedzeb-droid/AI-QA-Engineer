Author: Srivani Muniganti

This repository demonstrates an AI Quality Engineering Platform built by Srivani Muniganti.

# AI Quality Engineering Platform

An AI-powered quality engineering platform that automates the full QA lifecycle — from ingesting requirements to generating Playwright test scripts, executing them, analyzing failures, and self-healing broken locators using LLM suggestions.

Built with **LangChain (LCEL)**, **Streamlit**, **SQLite**, and **Playwright**. Supports Groq (Llama 3.3 70B), Anthropic Claude, Google Gemini, and Ollama as pluggable AI providers.

---

## Features

- **Requirements Ingestion** — parse free-text, Jira-style, or uploaded requirements into structured format
- **AI Test Case Generation** — generate happy-path, negative, and edge-case test cases from requirements
- **Playwright Script Generation** — produce ready-to-run `pytest` + Playwright Python scripts automatically
- **Test Execution** — run generated tests with pass/fail tracking, duration, and output capture
- **AI Failure Analysis** — root cause classification, severity scoring, and fix suggestions for failed tests
- **Self-Healing Engine** — auto-extract broken locators, query live DOM, and apply AI-suggested fixes
- **Analytics Dashboard** — quality score, pass rate trends, healing stats, and JSON/CSV report export
- **Pluggable AI Providers** — swap Groq ↔ Anthropic ↔ Google ↔ Ollama by changing one line in `.env`

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| AI / LLM | LangChain LCEL (Groq, Anthropic, Google, Ollama) |
| Database | SQLite via SQLAlchemy 2.x |
| Test Automation | Playwright + pytest |
| Config | Pydantic Settings + python-dotenv |
| Reporting | pytest-html, pytest-json-report, Allure |

---

## Quick Start

### Prerequisites

- Python 3.11+
- A free [Groq API key](https://console.groq.com) (or key for another supported provider)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/SrivaniMuniganti/ai-quality-engineering-platform.git
cd ai-quality-engineering-platform

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Configure environment
cp .env.example .env
# Edit .env — set GROQ_API_KEY (and optionally PLATFORM_PASSWORD)

# 4. Run the app
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) and log in with the credentials set in `.env` (default: `admin` / `demo1234`).

---

## Environment Configuration

```env
# AI Provider — choose one: groq | anthropic | google | ollama
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here     # free at console.groq.com

# Optional alternative providers
# AI_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_key_here

# AI_PROVIDER=google
# GOOGLE_API_KEY=your_google_key_here

# AI_PROVIDER=ollama   (no key needed — requires Ollama running locally)

# Target application under test — point this at localhost or a live site.
# Switch between environments by changing this value (no code changes needed).
BASE_URL=http://localhost:3000
# BASE_URL=https://your-live-site.example.com

# Target app login (leave blank if the app needs no login)
LOGIN_USERNAME=
LOGIN_PASSWORD=
LOGIN_USERNAME_SELECTOR=input[name="username"]
LOGIN_PASSWORD_SELECTOR=input[name="password"]
LOGIN_SUBMIT_SELECTOR=button[type="submit"]
LOGIN_SUCCESS_URL_PATTERN=

# App login (to this Streamlit platform, not the target app)
PLATFORM_USERNAME=admin
PLATFORM_PASSWORD=your-strong-password

# Browser
HEADLESS_BROWSER=false
```

Only the selected provider's API key is required. See `.env.example` for all options.

### Testing your own product

This platform no longer assumes any specific target app. Set `BASE_URL` to your product — a `localhost` dev
server or a live site — and generated tests will navigate there via the `base_url`/`page`/`logged_in_page`
fixtures in `generated_tests/conftest.py`. If your app requires login, set `LOGIN_USERNAME`/`LOGIN_PASSWORD`
and (if your login form differs from the defaults) the `LOGIN_*_SELECTOR` fields. You can switch between
localhost and a live site at any time just by changing `BASE_URL` and re-running — no restart required beyond
re-running the pipeline/tests, since `execution_service.py` re-reads `.env` at execution time.

SauceDemo examples (the "Seed Example Requirements" button, the Jira-simulation demo stories) are still bundled
as a working demo — they're optional and don't affect testing your own product via the Manual Text / File Upload
requirement inputs.

---

## Project Structure

```
app.py                          # Streamlit entry point + login
core/
  config.py                     # Pydantic settings (reads .env)
  models.py                     # SQLAlchemy ORM models
  database.py                   # SQLite init + session factory
  security.py                   # Input sanitization + path validation
chains/
  __init__.py                   # get_llm() — single AI provider factory
  requirement_parser_chain.py   # Text → structured requirements (JSON)
  testcase_generator_chain.py   # Requirement → test cases (JSON)
  script_generator_chain.py     # Test case → Playwright pytest script
  failure_analyzer_chain.py     # Failure output → root cause (JSON)
  self_healing_chain.py         # Broken locator + DOM → fix suggestions (JSON)
services/
  requirement_service.py        # Requirements CRUD + parse
  testcase_service.py           # Test case CRUD + generate
  script_service.py             # Script CRUD + generate
  execution_service.py          # Run pytest, collect results, trigger healing
  healing_service.py            # Orchestrate self-healing workflow
pages/
  1_Dashboard.py                # KPIs, charts, quality score
  2_Pipeline.py                 # Full end-to-end pipeline runner
  3_Requirements.py             # Ingest requirements
  4_Test_Cases.py               # Generate test cases
  5_Scripts.py                  # Generate Playwright scripts
  6_Execution.py                # Run tests + view results
  7_Failure_Analysis.py         # AI failure analysis
  8_Self_Healing.py             # Auto-heal broken locators
self_healing_engine/
  dom_analyzer.py               # Live DOM extraction via Playwright
  locator_healer.py             # AI locator suggestions
  retry_engine.py               # Full heal orchestration
qa_analytics_dashboard/
  metrics_engine.py             # Quality score + trend computation
  report_builder.py             # JSON / CSV export
generated_tests/
  conftest.py                   # pytest fixtures (page, logged_in_page)
  test_*.py                     # AI-generated scripts (git-ignored)
```

---

## Running Tests

```bash
# Run all generated tests
pytest generated_tests/ -v --tb=short

# Run a single test file
pytest generated_tests/test_login.py -v

# Run with HTML report
pytest generated_tests/ -v --html=reports/report.html --self-contained-html

# Run with JSON report
pytest generated_tests/ -v --json-report --json-report-file=reports/test_results.json
```

---

## Pipeline Overview

```
User Input
    │
    ▼
Requirements (free text / Jira / file)
    │  requirement_parser_chain
    ▼
Test Cases (happy-path, negative, edge)
    │  testcase_generator_chain
    ▼
Playwright Scripts (pytest + Playwright Python)
    │  script_generator_chain
    ▼
Test Execution (pytest subprocess + JSON logs)
    │  execution_service
    ▼
Failure Analysis (root cause, severity, fix)
    │  failure_analyzer_chain
    ▼
Self-Healing (DOM diff → AI locator fix → retry)
       self_healing_chain + retry_engine
```

---

## Database Schema

```
Requirement ──< TestCase ──< Script ──< TestRun ──< Analysis
                                                 └─< HealingAttempt
```

Stored at `data/qa_platform.db` (SQLite, git-ignored).

---

## Security

- **Path traversal prevention** — `validate_script_path()` ensures executed scripts resolve inside `generated_tests/`
- **Script validation** — AI-generated scripts must begin with `import` or `from`
- **Input sanitization** — `sanitize_input()` strips prompt injection patterns, limits to 5000 chars
- **Safe execution** — `execution_service` accepts only a `script_id`; the path is fetched from DB, never from user input

---

## Documentation

| File | Description |
|---|---|
| `documentation/architecture.md` | System design, data flow, module breakdown |
| `documentation/demo-guide.md` | Step-by-step demo walkthrough |
| `documentation/ai-prompts.md` | All 5 LangChain prompt templates with examples |

---

## Target Application

The target app under test is configurable — set `BASE_URL` in `.env` to point at a localhost dev server or a
live site (see [Testing your own product](#testing-your-own-product) above). Out of the box it defaults to
`http://localhost:3000`; the bundled example requirements/demo data reference [SauceDemo](https://www.saucedemo.com),
a publicly available e-commerce demo app, purely as a working demo you can try before pointing the platform at
your own product.

---

## License

MIT
