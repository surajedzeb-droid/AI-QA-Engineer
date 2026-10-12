from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from chains import get_llm
from shared.utils import extract_json as _extract_json


def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a QA requirements analyst. Analyze the requirements text for whatever application
it describes (it may be a web app running on localhost or a live site) — do not assume any specific product.
Return a JSON object with key "requirements" containing a list.
Each item must have these exact fields:
- title: short descriptive title
- description: detailed description of what needs to be tested
- feature: a short feature/module name inferred from the text (e.g. Login, Search, Checkout, Settings)
- priority: one of [High, Medium, Low]
- acceptance_criteria: bullet-point acceptance criteria as a single string
- test_types: comma-separated list from [Functional, Negative, UI, Performance, Security]

Return ONLY valid JSON. No markdown fences. No extra text."""),
        ("human", "Parse these requirements:\n\n{text}"),
    ])
    return prompt | get_llm() | StrOutputParser()


def parse_requirements(text: str) -> list:
    raw = get_chain().invoke({"text": text})
    data = _extract_json(raw)
    if isinstance(data, dict) and "requirements" in data:
        return data["requirements"]
    if isinstance(data, list):
        return data
    return []
