import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains import get_llm
from shared.utils import extract_json as _extract_json


def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a senior QA analyst. You are given a structural summary of a real website
(its title, navigation links, headings, forms, and buttons) extracted by crawling the live page.

Suggest 3 to 6 concrete, testable features for this specific site, grounded in what was actually found —
do not invent features that have no evidence in the summary (e.g. don't suggest "Checkout" unless a cart/
checkout-related link, heading, or form field was found).

Return a JSON object with key "suggestions" containing a list. Each item must have:
- feature: short feature/module name (e.g. "Contact Form", "Navigation", "Homepage Load")
- description: one or two sentences describing what should be tested, referencing the real elements found
  (actual link text, button text, or form field names from the summary)

Return ONLY valid JSON. No markdown fences. No extra text."""),
        ("human", """Site summary (url: {url}):

Title: {title}
Navigation links: {nav_links}
Headings: {headings}
Buttons: {buttons}
Forms (field names per form): {forms}"""),
    ])
    return prompt | get_llm() | StrOutputParser()


def suggest_features(site_summary: dict) -> list:
    if site_summary.get("error"):
        return []

    raw = get_chain().invoke({
        "url": site_summary.get("url", ""),
        "title": site_summary.get("title", ""),
        "nav_links": ", ".join(site_summary.get("nav_links", [])) or "(none found)",
        "headings": ", ".join(site_summary.get("headings", [])) or "(none found)",
        "buttons": ", ".join(site_summary.get("buttons", [])) or "(none found)",
        "forms": json.dumps(site_summary.get("forms", [])) if site_summary.get("forms") else "(none found)",
    })
    data = _extract_json(raw)
    if isinstance(data, dict) and "suggestions" in data:
        return data["suggestions"]
    if isinstance(data, list):
        return data
    return []
