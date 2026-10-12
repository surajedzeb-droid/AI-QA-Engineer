"""Extracts interactive element selectors from the target app under test using Playwright."""
from __future__ import annotations


class DOMAnalyzer:
    def extract_locators(
        self,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        username_selector: str | None = None,
        password_selector: str | None = None,
        submit_selector: str | None = None,
    ) -> dict[str, list[str]]:
        """Browse the configured target app (BASE_URL) and return selectors for all interactive elements.

        Returns a dict: {element_description: [selector_candidates]}.
        Falls back to a static registry if Playwright is unavailable or the app can't be reached.
        """
        from core.config import settings

        url = url or settings.BASE_URL
        username = username if username is not None else settings.LOGIN_USERNAME
        password = password if password is not None else settings.LOGIN_PASSWORD
        username_selector = username_selector or settings.LOGIN_USERNAME_SELECTOR
        password_selector = password_selector or settings.LOGIN_PASSWORD_SELECTOR
        submit_selector = submit_selector or settings.LOGIN_SUBMIT_SELECTOR

        try:
            return self._dynamic_extract(
                url, username, password, username_selector, password_selector, submit_selector
            )
        except Exception:
            return self._static_fallback()

    def _dynamic_extract(
        self,
        url: str,
        username: str,
        password: str,
        username_selector: str,
        password_selector: str,
        submit_selector: str,
    ) -> dict[str, list[str]]:
        from playwright.sync_api import sync_playwright

        result: dict[str, list[str]] = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # --- Initial page ---
            page.goto(url)
            page.wait_for_load_state("networkidle")
            result.update(self._collect_elements(page, "initial"))

            # --- Post-login page (only if credentials are configured) ---
            if username and password:
                try:
                    page.fill(username_selector, username)
                    page.fill(password_selector, password)
                    page.click(submit_selector)
                    page.wait_for_load_state("networkidle")
                    result.update(self._collect_elements(page, "after_login"))
                except Exception:
                    pass

            browser.close()

        return result

    def _collect_elements(self, page, context: str) -> dict[str, list[str]]:
        selectors: dict[str, list[str]] = {}
        elements = page.query_selector_all(
            "button, input, a, [data-test], [id], [class]"
        )
        for el in elements:
            try:
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                el_id = el.get_attribute("id") or ""
                el_class = (el.get_attribute("class") or "").split()[0] if el.get_attribute("class") else ""
                data_test = el.get_attribute("data-test") or ""
                text = (el.inner_text() or "")[:30].strip()

                candidates = []
                if data_test:
                    candidates.append(f"[data-test='{data_test}']")
                if el_id:
                    candidates.append(f"#{el_id}")
                if el_class:
                    candidates.append(f".{el_class}")
                if text:
                    candidates.append(f"{tag}:has-text('{text}')")

                if candidates:
                    key = f"{context}_{data_test or el_id or el_class or text or tag}"
                    selectors[key] = candidates
            except Exception:
                continue
        return selectors

    def _static_fallback(self) -> dict[str, list[str]]:
        """Return generic common-pattern selector guesses when live extraction fails
        (e.g. the target app under test couldn't be reached)."""
        return {
            "login_username": ["input[name='username']", "input[type='email']", "#username"],
            "login_password": ["input[name='password']", "input[type='password']", "#password"],
            "login_button": ["button[type='submit']", "button:has-text('Log in')", "button:has-text('Sign in')"],
            "login_error": [".error-message", "[role='alert']", ".error"],
            "nav_menu": ["nav", "[role='navigation']"],
            "logout": ["a:has-text('Logout')", "button:has-text('Logout')", "#logout"],
        }


def extract_locators_safe() -> dict[str, list[str]]:
    """Run DOMAnalyzer().extract_locators() in a separate process.

    Streamlit runs on Tornado, which forces asyncio's SelectorEventLoop policy on Windows, but Playwright's
    sync API needs ProactorEventLoop to spawn its browser subprocess — calling it in-process from a
    Streamlit page would silently fall back to the generic static registry instead of real DOM data.
    A fresh subprocess starts with the default (Proactor) policy, avoiding that.
    """
    import json
    import os
    import subprocess
    import sys

    project_root = os.path.dirname(os.path.dirname(__file__))
    try:
        result = subprocess.run(
            [sys.executable, "-m", "self_healing_engine.dom_analyzer"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=project_root,
        )
        if result.returncode != 0:
            return DOMAnalyzer()._static_fallback()
        return json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        return DOMAnalyzer()._static_fallback()


def summarize_dom_for_context(dom_context: dict, hint_text: str, max_chars: int = 3000) -> str:
    """Rank dom_context entries by relevance to hint_text (a broken locator, or a test
    name + script content) and return a JSON summary truncated to max_chars.

    On a large page the DOM dump can have hundreds of entries — blind truncation in
    dict-iteration order means the one real selector/heading/text an LLM actually needs
    may never survive the character budget. Ranking by keyword overlap first fixes that.
    """
    import json
    import re

    # Split camelCase before lowercasing (e.g. "callbackModal" -> "callback modal")
    # so keyword matching works word-by-word instead of as one unmatchable blob.
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", hint_text)
    keywords = set(w for w in re.findall(r"[a-z]+", spaced.lower()) if len(w) > 2)

    def relevance(item: tuple[str, list]) -> int:
        key, candidates = item
        text = (key + " " + " ".join(candidates)).lower()
        return sum(1 for kw in keywords if kw in text)

    ranked = sorted(dom_context.items(), key=relevance, reverse=True)
    return json.dumps(dict(ranked), indent=2)[:max_chars]


if __name__ == "__main__":
    import json

    print(json.dumps(DOMAnalyzer().extract_locators()))
