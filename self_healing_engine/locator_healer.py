"""Uses the self_healing_chain to suggest replacement locators."""
from chains.self_healing_chain import suggest_alternative_locators
from self_healing_engine.dom_analyzer import summarize_dom_for_context


class LocatorHealer:
    def heal(
        self,
        broken_locator: str,
        dom_context: dict,
        failure_output: str,
    ) -> dict:
        """
        Returns:
          {original, alternatives, confidence, strategy, explanation}
        """
        dom_summary = summarize_dom_for_context(dom_context, broken_locator)
        result = suggest_alternative_locators(
            broken_locator=broken_locator,
            failure_message=failure_output,
            available_dom_selectors=dom_summary,
        )
        return {
            "original": broken_locator,
            "alternatives": result.get("alternative_locators", []),
            "confidence": result.get("confidence", 0.0),
            "strategy": result.get("strategy", "css"),
            "explanation": result.get("explanation", ""),
        }
