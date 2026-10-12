from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains import get_llm
from shared.utils import extract_json as _extract_json


def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a senior QA engineer creating detailed test cases for the application under test, based solely
on the requirement provided below (it may be a web app running on localhost or a live site) — do not assume any specific product.

You may be given a summary of real elements found on the live target page (available_dom_context below — may be
empty if unavailable). The requirement text was written by a person and may describe a button, page, or element
that doesn't actually match what's on the live site (wrong label, a page that doesn't exist, etc.) — ground your
steps/test_data in the real DOM context when it's available rather than assuming the requirement's wording is
accurate. If something the requirement describes isn't corroborated by the DOM context, don't invent a plausible
specific selector, CSS class, or page path for it — write that test case's test_data as
"NOT CONFIRMED ON LIVE PAGE — verify this element/page exists before relying on this test" instead of fabricating one.

Return a JSON object with key "test_cases" containing a list.
Each item must have these exact fields:
- title: descriptive test case title
- description: what this test case verifies
- test_type: one of [Functional, Negative, UI, Performance, Security]
- priority: one of [High, Medium, Low]
- preconditions: what must be true before the test runs
- steps: numbered step-by-step instructions as a single string
- expected_result: what should happen if the test passes
- test_data: specific data values to use (usernames, passwords, form values)

Return ONLY valid JSON. No markdown fences. No extra text."""),
        ("human", """Requirement:
Title: {title}
Description: {description}
Feature: {feature}
Acceptance Criteria: {acceptance_criteria}
Test Types: {test_types}

Available DOM context from the live target page (selectors and visible text actually found there — may be empty if unavailable):
{dom_context}

Generate thorough test cases covering all acceptance criteria and test types specified."""),
    ])
    return prompt | get_llm() | StrOutputParser()


def generate_test_cases(requirement: dict, dom_context: str = "") -> list:
    raw = get_chain().invoke({
        "title": requirement.get("title", ""),
        "description": requirement.get("description", ""),
        "feature": requirement.get("feature", ""),
        "acceptance_criteria": requirement.get("acceptance_criteria", ""),
        "test_types": requirement.get("test_types", "Functional"),
        "dom_context": dom_context or "(not available)",
    })
    data = _extract_json(raw)
    if isinstance(data, dict) and "test_cases" in data:
        return data["test_cases"]
    if isinstance(data, list):
        return data
    return []
