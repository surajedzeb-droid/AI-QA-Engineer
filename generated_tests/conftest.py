import os
import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, BrowserContext

# Load .env directly so BASE_URL/LOGIN_* are picked up even when this file runs
# as its own pytest subprocess (env vars set only in .env, not the OS environment).
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
LOGIN_USERNAME = os.getenv("LOGIN_USERNAME", "")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
LOGIN_USERNAME_SELECTOR = os.getenv("LOGIN_USERNAME_SELECTOR", 'input[name="username"]')
LOGIN_PASSWORD_SELECTOR = os.getenv("LOGIN_PASSWORD_SELECTOR", 'input[name="password"]')
LOGIN_SUBMIT_SELECTOR = os.getenv("LOGIN_SUBMIT_SELECTOR", 'button[type="submit"]')
LOGIN_SUCCESS_URL_PATTERN = os.getenv("LOGIN_SUCCESS_URL_PATTERN", "")
HEADLESS = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", os.path.join(os.path.dirname(__file__), "..", "reports", "screenshots"))


@pytest.fixture(scope="session")
def base_url():
    """The target app under test — set BASE_URL in .env to point at localhost or a live site."""
    return BASE_URL


@pytest.fixture(scope="function")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=None,
            base_url=BASE_URL,
        )
        pg = context.new_page()
        pg.set_default_timeout(30000)
        yield pg
        context.close()
        browser.close()


@pytest.fixture(scope="function")
def logged_in_page(page: Page):
    """Page navigated to BASE_URL and logged in using LOGIN_USERNAME/LOGIN_PASSWORD from .env.

    If no credentials are configured, just navigates to BASE_URL without logging in
    (use this when the target app doesn't require auth).
    """
    page.goto(BASE_URL)
    if LOGIN_USERNAME and LOGIN_PASSWORD:
        page.fill(LOGIN_USERNAME_SELECTOR, LOGIN_USERNAME)
        page.fill(LOGIN_PASSWORD_SELECTOR, LOGIN_PASSWORD)
        page.click(LOGIN_SUBMIT_SELECTOR)
        if LOGIN_SUCCESS_URL_PATTERN:
            page.wait_for_url(LOGIN_SUCCESS_URL_PATTERN)
    return page


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        try:
            page = item.funcargs.get("page") or item.funcargs.get("logged_in_page")
            if page:
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                screenshot_path = os.path.join(SCREENSHOT_DIR, f"{item.name}.png")
                page.screenshot(path=screenshot_path)
        except Exception:
            pass
