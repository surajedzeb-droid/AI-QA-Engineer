from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains import get_llm
from shared.utils import extract_json as _extract_json


def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a senior QA automation engineer specializing in test failure analysis for Playwright + pytest tests against a web application under test (target may be localhost or a live site).

Analyze the test failure and return a JSON object with these exact fields:
- root_cause: clear explanation of what caused the failure (1-3 sentences)
- failure_category: one of [ElementNotFound, TimeoutError, AssertionError, NetworkError, AuthenticationError, ScriptError, EnvironmentError]
- suggested_fix: step-by-step fix instructions as a string
- fixed_script: if the provided script has bugs, return the corrected complete Python script as a string. Otherwise return null.
- severity: one of [Critical, High, Medium, Low] based on impact

When you write fixed_script, you may be given a summary of real selectors/text found on the live target page
(available_dom_context below) — use it to ground every locator and expected value in the ENTIRE script, not
just the line that raised the reported error. The script may already contain other assertions (titles, URL
paths, heading text, etc.) that were never reached because the test crashed before them — those are just as
likely to be wrong as the one that actually failed, and leaving them in place only guarantees the next run
fails too. So: for every assertion in the script, if its expected value isn't backed by available_dom_context,
the original script's own evidence, or the failure output, replace it with a structural check (element is
visible, URL changed from the starting page, no console errors) instead — do not leave an unverified literal
value in place just because it wasn't the one that raised this particular error. Do NOT invent new specific
expected values of your own either (e.g. assuming a generic "/home" URL or a placeholder app name) — that is
exactly the kind of bug you are being asked to remove, not add.

fixed_script must be the Python sync Playwright API, not JavaScript: `.first`, `.last`, and `.count` on a
Locator are PROPERTIES with no parentheses (`locator.first.click()`), not methods — `locator.first()` raises
TypeError in Python.

Return ONLY valid JSON. No markdown fences. No extra text."""),
        ("human", """Test Name: {test_name}

Failure Output:
{failure_output}

{script_section}

Available DOM context from the live target page (selectors and visible text actually found there — may be empty if unavailable):
{dom_context}"""),
    ])
    return prompt | get_llm() | StrOutputParser()


def analyze_failure(test_name: str, failure_output: str, script_content: str = "", dom_context: str = "") -> dict:
    script_section = ""
    if script_content:
        script_section = f"Original Script:\n```python\n{script_content[:2000]}\n```"

    raw = get_chain().invoke({
        "test_name": test_name,
        "failure_output": failure_output[:3000],
        "script_section": script_section,
        "dom_context": dom_context or "(not available)",
    })
    return _extract_json(raw)
