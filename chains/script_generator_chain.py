from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains import get_llm

PLAYWRIGHT_CONTEXT = """You are a senior QA automation engineer writing Playwright + pytest tests for the application under test.
The target is whatever app the test case describes (it may run on localhost or a live site) — use the selectors,
field names, and flows given in the test case's Preconditions/Steps/Test Data; do not assume any specific product.

STRICT RULES — follow exactly:
1. Start with imports: import pytest, import os, from playwright.sync_api import Page
2. NEVER define a `page` fixture — it is already provided by conftest.py via sync_playwright
3. NEVER define a `logged_in_page` fixture — it is already provided by conftest.py
4. NEVER define a `base_url` fixture — it is already provided by conftest.py and returns the BASE_URL from .env
5. Just write test functions that accept `page`, `logged_in_page`, and/or `base_url` as parameters — pytest injects them automatically
6. If the test requires login, prefer the `logged_in_page` fixture (already authenticated) instead of logging in manually
7. If the test needs a fresh unauthenticated page, use `page` + `base_url` fixtures: page.goto(base_url)
8. Prefer resilient selectors in this order: a matching real selector/text from the available DOM context given below > explicit selectors/field names given in the test case > role/label/text locators (page.get_by_role, page.get_by_label, page.get_by_text) > CSS id/name/class. Never invent a CSS class, data-test attribute, or URL path that isn't backed by the DOM context or the test case itself — the test case's wording may describe something that doesn't actually match the live page.
9. Add page.wait_for_selector() / page.wait_for_url() / page.wait_for_load_state() before assertions
10. This is the Python sync API, not JavaScript: `.first`, `.last`, and `.count` on a Locator are PROPERTIES
    with no parentheses (`locator.first.click()`), not methods (`locator.first()` raises TypeError in Python).
11. Return ONLY valid Python code, no markdown fences, no explanation

CORRECT PATTERN:
import pytest
from playwright.sync_api import Page

def test_example(base_url, page: Page):
    page.goto(base_url)
    page.get_by_label("Username").fill("testuser")
    page.get_by_label("Password").fill("testpass")
    page.get_by_role("button", name="Log in").click()
    page.wait_for_load_state("networkidle")
    assert page.url != base_url"""


def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", PLAYWRIGHT_CONTEXT),
        ("human", """Generate a complete Playwright + pytest script for:

Title: {title}
Feature: {feature}
Test Type: {test_type}
Preconditions: {preconditions}
Steps: {steps}
Expected Result: {expected_result}
Test Data: {test_data}

Available DOM context from the live target page (selectors and visible text actually found there — may be empty if unavailable):
{dom_context}

Return ONLY the Python code, starting with import statements."""),
    ])

    return prompt | get_llm() | StrOutputParser()


def _strip_conflicting_fixtures(code: str) -> str:
    """Remove any @pytest.fixture def page / logged_in_page blocks the LLM generated.
    These are already provided by conftest.py and must not be redefined."""
    import re
    # Remove fixture blocks for 'page' and 'logged_in_page'
    pattern = r'@pytest\.fixture[^\n]*\n(?:[ \t]+.*\n)*?[ \t]*def (?:page|logged_in_page)\(.*?\):[^\n]*\n(?:(?:[ \t]+.*\n?)|(?:\n))*'
    cleaned = re.sub(pattern, '', code)
    return cleaned.strip()


def generate_script(test_case: dict, dom_context: str = "") -> str:
    chain = get_chain()
    raw = chain.invoke({
        "title": test_case.get("title", ""),
        "feature": test_case.get("feature", ""),
        "test_type": test_case.get("test_type", "Functional"),
        "preconditions": test_case.get("preconditions", ""),
        "steps": test_case.get("steps", ""),
        "expected_result": test_case.get("expected_result", ""),
        "test_data": test_case.get("test_data", ""),
        "dom_context": dom_context or "(not available)",
    })
    # Strip markdown fences if LLM wrapped in them
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    # Remove any page/logged_in_page fixture redefinitions
    raw = _strip_conflicting_fixtures(raw)
    return raw
