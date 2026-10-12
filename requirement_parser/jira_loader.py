"""Simulates Jira story ingestion and file-based requirement loading."""
from __future__ import annotations
from typing import List

JIRA_STORIES: dict[str, List[dict]] = {
    "Demo: SauceDemo Sprint 1": [
        {
            "title": "Valid Login with Standard User",
            "description": "A standard user can log in with correct credentials and be redirected to the products page.",
            "feature": "Login",
            "priority": "High",
            "acceptance_criteria": "Given valid credentials, user sees the products inventory page.",
            "test_types": "Functional,Smoke",
        },
        {
            "title": "Invalid Login Shows Error",
            "description": "Users who enter wrong credentials see an appropriate error message.",
            "feature": "Login",
            "priority": "High",
            "acceptance_criteria": "Error banner 'Username and password do not match' is displayed.",
            "test_types": "Functional,Negative",
        },
        {
            "title": "Locked Out User Cannot Login",
            "description": "Locked-out users are blocked with an error message explaining the account is locked.",
            "feature": "Login",
            "priority": "Medium",
            "acceptance_criteria": "Error message references locked account.",
            "test_types": "Functional,Negative",
        },
        {
            "title": "Products Page Displays All Items",
            "description": "After login, the inventory page must display all 6 products with names, prices, and images.",
            "feature": "Inventory",
            "priority": "High",
            "acceptance_criteria": "6 product cards visible; each has title, price, and 'Add to cart' button.",
            "test_types": "Functional,UI",
        },
        {
            "title": "Sort Products by Price Low to High",
            "description": "Users can sort products by price ascending.",
            "feature": "Inventory",
            "priority": "Medium",
            "acceptance_criteria": "First product has the lowest price after sorting.",
            "test_types": "Functional",
        },
        {
            "title": "Add Single Item to Cart",
            "description": "Clicking 'Add to cart' increments the cart badge by 1.",
            "feature": "Cart",
            "priority": "High",
            "acceptance_criteria": "Cart badge shows '1' after adding one item.",
            "test_types": "Functional,Smoke",
        },
        {
            "title": "Remove Item from Cart",
            "description": "Users can remove items from the cart and the badge decrements.",
            "feature": "Cart",
            "priority": "High",
            "acceptance_criteria": "Cart badge disappears or decrements when item is removed.",
            "test_types": "Functional",
        },
        {
            "title": "Checkout with Valid Information",
            "description": "Users can complete checkout by providing first name, last name, and zip.",
            "feature": "Checkout",
            "priority": "High",
            "acceptance_criteria": "'Thank you for your order' confirmation is displayed.",
            "test_types": "Functional,E2E",
        },
        {
            "title": "Checkout Fails Without Required Fields",
            "description": "Leaving checkout fields blank shows validation errors.",
            "feature": "Checkout",
            "priority": "Medium",
            "acceptance_criteria": "Error message shown for missing first name / zip.",
            "test_types": "Functional,Negative",
        },
        {
            "title": "Logout Clears Session",
            "description": "After logout the user is redirected to the login page and cannot navigate back.",
            "feature": "Login",
            "priority": "Medium",
            "acceptance_criteria": "User is on login page; back button does not restore session.",
            "test_types": "Functional,Security",
        },
    ],
    "Demo: SauceDemo Sprint 2": [
        {
            "title": "Product Detail Page Loads Correctly",
            "description": "Clicking a product name opens the detail page with description and price.",
            "feature": "Inventory",
            "priority": "Medium",
            "acceptance_criteria": "Detail page shows product name, image, description, and price.",
            "test_types": "Functional,UI",
        },
        {
            "title": "Add to Cart from Detail Page",
            "description": "User can add a product to the cart directly from its detail page.",
            "feature": "Cart",
            "priority": "Medium",
            "acceptance_criteria": "Cart badge increments after clicking 'Add to cart' on detail page.",
            "test_types": "Functional",
        },
        {
            "title": "Cart Persists After Navigation",
            "description": "Items added to the cart remain when user navigates away and returns.",
            "feature": "Cart",
            "priority": "Medium",
            "acceptance_criteria": "Cart badge count unchanged after returning to inventory.",
            "test_types": "Functional",
        },
        {
            "title": "Sort Products by Name Z to A",
            "description": "Users can sort products alphabetically descending.",
            "feature": "Inventory",
            "priority": "Low",
            "acceptance_criteria": "Products are listed in Z–A order after selecting that sort option.",
            "test_types": "Functional",
        },
        {
            "title": "Performance Glitch User Experiences Delay",
            "description": "The performance_glitch_user account simulates a slow-loading app.",
            "feature": "Performance",
            "priority": "Low",
            "acceptance_criteria": "Login succeeds but page load takes noticeably longer than standard_user.",
            "test_types": "Performance",
        },
        {
            "title": "Checkout Overview Shows Correct Totals",
            "description": "The checkout overview page correctly calculates item total, tax, and final total.",
            "feature": "Checkout",
            "priority": "High",
            "acceptance_criteria": "Item total + tax = displayed total.",
            "test_types": "Functional",
        },
        {
            "title": "Continue Shopping from Cart",
            "description": "User can return to inventory from the cart page without losing cart contents.",
            "feature": "Cart",
            "priority": "Low",
            "acceptance_criteria": "Cart item count unchanged after clicking 'Continue Shopping'.",
            "test_types": "Functional",
        },
        {
            "title": "Hamburger Menu Opens and Closes",
            "description": "The hamburger menu opens and its items (All Items, About, Logout, Reset) are visible.",
            "feature": "Navigation",
            "priority": "Low",
            "acceptance_criteria": "Menu opens on click; all four menu items present.",
            "test_types": "Functional,UI",
        },
        {
            "title": "Reset App State Clears Cart",
            "description": "Using 'Reset App State' from the menu clears all cart items.",
            "feature": "Navigation",
            "priority": "Medium",
            "acceptance_criteria": "Cart badge disappears after reset.",
            "test_types": "Functional",
        },
        {
            "title": "Visual Regression on Login Page",
            "description": "Login page matches the approved baseline screenshot.",
            "feature": "Login",
            "priority": "Low",
            "acceptance_criteria": "Screenshot diff below 1% threshold.",
            "test_types": "Visual",
        },
    ],
}


class JiraLoader:
    """Loads requirements from various sources and returns list of dicts."""

    def simulate_jira_stories(self, project: str) -> list[dict]:
        """Return pre-built Jira story set for the given project name."""
        return JIRA_STORIES.get(project, [])

    def available_projects(self) -> list[str]:
        return list(JIRA_STORIES.keys())

    def load_from_text(self, text: str) -> list[dict]:
        """Wrap plain text as a single requirement dict for downstream parsing."""
        return [
            {
                "title": "Requirement from text",
                "description": text.strip(),
                "feature": "General",
                "priority": "Medium",
                "acceptance_criteria": "",
                "test_types": "Functional",
            }
        ]

    def load_from_file(self, content: str) -> list[dict]:
        """Parse uploaded file content — each non-empty line becomes a requirement."""
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        requirements = []
        for i, line in enumerate(lines, 1):
            requirements.append(
                {
                    "title": f"Requirement {i}",
                    "description": line,
                    "feature": "General",
                    "priority": "Medium",
                    "acceptance_criteria": "",
                    "test_types": "Functional",
                }
            )
        return requirements
