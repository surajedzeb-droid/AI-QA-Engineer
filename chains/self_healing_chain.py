from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains import get_llm
from shared.utils import extract_json as _extract_json


def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Playwright self-healing automation expert. A test locator has broken against the
application under test (localhost or a live site — do not assume any specific product). Analyse the failure
context and available DOM selectors, then suggest alternatives.

Return ONLY valid JSON with these exact fields:
- alternative_locators: list of selector strings ordered best-first (up to 5)
- confidence: float 0.0-1.0 representing your confidence the first alternative will work
- strategy: one of [data-test, aria, css, xpath, text]
- explanation: one or two sentences explaining why the locator broke and why the alternatives should work

No markdown fences. No extra text."""),
        ("human", """Broken locator: {broken_locator}

Failure message:
{failure_message}

Available DOM selectors from live page:
{available_dom_selectors}"""),
    ])
    return prompt | get_llm() | StrOutputParser()


def suggest_alternative_locators(
    broken_locator: str,
    failure_message: str,
    available_dom_selectors: str,
) -> dict:
    raw = get_chain().invoke({
        "broken_locator": broken_locator,
        "failure_message": failure_message[:2000],
        "available_dom_selectors": available_dom_selectors[:3000],
    })
    return _extract_json(raw)
