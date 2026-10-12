import json
import re
from datetime import datetime, timezone


def extract_json(text: str) -> dict | list:
    """Parse an LLM response as JSON, stripping markdown fences first.

    If the response was truncated mid-generation (e.g. the model hit its token limit
    partway through a string or list item — a real failure mode with large structured
    outputs), falls back to repairing it: truncate back to the last structurally valid
    position and close any open brackets, so a partial-but-truncated response yields
    the items that *did* generate instead of crashing with JSONDecodeError.

    Raises json.JSONDecodeError if the text isn't JSON at all (not just truncated).
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(text)
        if repaired is not None:
            return json.loads(repaired)
        raise


def _repair_truncated_json(text: str) -> str | None:
    """Best-effort repair for JSON cut off mid-string/mid-item. Scans for the last
    position where brackets are balanced and we're not inside an open string, truncates
    there, drops a dangling trailing comma, and closes any still-open brackets.
    Returns None if the text has no unclosed brackets (so the error is something else)."""
    stack = []
    in_string = False
    escape = False
    last_safe = 0

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
        if ch in ",}]":
            last_safe = i + 1

    if not stack:
        return None

    truncated = text[:last_safe].rstrip()
    if truncated.endswith(","):
        truncated = truncated[:-1]

    closers = {"{": "}", "[": "]"}
    for opener in reversed(stack):
        truncated += closers[opener]
    return truncated


def safe_filename(name: str, max_len: int = 60) -> str:
    """Convert arbitrary string to a safe filename."""
    name = re.sub(r"[^\w\s-]", "", name).strip()
    name = re.sub(r"[\s]+", "_", name)
    return name[:max_len].lower()


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len - len(suffix)] + suffix


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
