"""Orchestrates the full self-healing flow for a failed test run."""
import re
from datetime import datetime

from core.database import get_session
from core.models import TestRun, Script, HealingAttempt
from self_healing_engine.dom_analyzer import extract_locators_safe
from self_healing_engine.locator_healer import LocatorHealer
from services.execution_service import execute_script


class RetryEngine:
    def retry_with_healing(self, run_id: int) -> dict:
        """
        1. Fetch failed run + original script
        2. Parse broken locator from failure output
        3. Extract live DOM selectors
        4. Call LocatorHealer for alternatives
        5. Patch script with best alternative
        6. Re-execute patched script
        7. Save HealingAttempt record
        Returns healing result dict.
        """
        db = get_session()
        try:
            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if not run:
                return {"status": "failed", "error": f"Run {run_id} not found"}

            if run.status not in ("failed", "error"):
                return {"status": "skipped", "reason": "Run is not in failed/error state"}

            script = db.query(Script).filter(Script.id == run.script_id).first()
            if not script:
                return {"status": "failed", "error": "Associated script not found"}

            failure_output = run.output or run.error_message or ""

            script_content = ""
            if script.script_path:
                try:
                    with open(script.script_path, "r", encoding="utf-8") as f:
                        script_content = f.read()
                except Exception:
                    pass

            # Get DOM context (needed for both locator detection and healing)
            dom_context = extract_locators_safe()

            # Extract broken locator. Prefer the traceback (precise: it's the line that
            # actually raised), but that only works when the failure surfaces a selector
            # string directly. Some locators fail inside a try/except the generated script
            # swallows (e.g. a modal-presence probe) and never appear in the traceback at
            # all — for those, fall back to cross-checking every selector literal used in
            # the script against the live DOM and flag the first one that doesn't exist.
            broken_locator = self._extract_locator(failure_output)
            if not broken_locator and script_content:
                broken_locator = self._find_broken_selector_in_script(script_content, dom_context)
            if not broken_locator:
                broken_locator = "unknown"

            # Heal
            healer = LocatorHealer()
            healing = healer.heal(broken_locator, dom_context, failure_output)
            alternatives = healing.get("alternatives", [])

            healed_script = None
            new_status = "failed"
            run_result = None

            if alternatives and script.script_path and broken_locator != "unknown" and broken_locator in script_content:
                # Patch script file with best alternative
                try:
                    code = script_content
                    patched = code.replace(broken_locator, alternatives[0])

                    with open(script.script_path, "w", encoding="utf-8") as f:
                        f.write(patched)

                    healed_script = patched

                    # Re-execute
                    run_result = execute_script(script.id)
                    new_status = "healed" if run_result.get("status") == "passed" else "failed"
                except Exception as e:
                    new_status = "failed"

            # Save HealingAttempt
            attempt = HealingAttempt(
                run_id=run_id,
                test_name=run.test_name,
                original_locator=broken_locator,
                suggested_locators=str(alternatives),
                healing_strategy=healing.get("strategy", "css"),
                healed_script=healed_script,
                status=new_status,
                confidence_score=healing.get("confidence", 0.0),
                created_at=datetime.utcnow(),
            )
            db.add(attempt)
            db.commit()
            db.refresh(attempt)

            return {
                "healing_attempt_id": attempt.id,
                "status": new_status,
                "original_locator": broken_locator,
                "alternatives": alternatives,
                "confidence": healing.get("confidence", 0.0),
                "strategy": healing.get("strategy"),
                "explanation": healing.get("explanation"),
                "new_run": run_result,
            }
        finally:
            db.close()

    def _extract_locator(self, output: str) -> str | None:
        """Extract the most likely broken selector from pytest output."""
        # Selectors like div[role='dialog'] mix quote types, so the capture must match to
        # the SAME quote character that opened the string, not stop at the first quote of
        # either kind.
        quoted = r"(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")"
        patterns = [
            r"page\.(?:locator|click|fill|wait_for_selector)\(\s*" + quoted,
            r"selector=" + quoted,
            r"No element matching selector\s+" + quoted,
        ]
        for pat in patterns:
            m = re.search(pat, output)
            if m:
                return m.group(1) if m.group(1) is not None else m.group(2)
        return None

    def _find_broken_selector_in_script(self, script_content: str, dom_context: dict) -> str | None:
        """Find a CSS-like selector literal used in the script that doesn't exist on the live page.

        Catches locators that fail inside the script's own try/except (so they never raise
        into the pytest traceback) by cross-checking every selector the script references
        against the live DOM extraction.
        """
        quoted = r"(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")"
        pattern = (
            r"\.(?:locator|click|fill|wait_for_selector|query_selector|query_selector_all|"
            r"is_visible|is_enabled|dblclick|check|uncheck|hover|select_option)\(\s*" + quoted
        )
        known_selectors = set()
        for candidates in dom_context.values():
            known_selectors.update(candidates)

        seen = []
        for m in re.finditer(pattern, script_content):
            sel = m.group(1) if m.group(1) is not None else m.group(2)
            # Only consider CSS-like selectors (#id, .class, [attr=...], tag) — skip text=/xpath=
            # prefixed ones, which this simple exact-match check isn't equipped to validate.
            if sel.startswith(("text=", "xpath=")):
                continue
            if sel not in seen:
                seen.append(sel)

        for sel in seen:
            if sel not in known_selectors:
                return sel
        return None
