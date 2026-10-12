"""Crawls the configured target app (BASE_URL) to summarize its structure for AI requirement suggestions.

Run as a module (`python -m requirement_parser.site_crawler <url>`) rather than imported-and-called
directly from Streamlit: Streamlit runs on Tornado, which forces asyncio's SelectorEventLoop policy on
Windows, but Playwright's sync API needs ProactorEventLoop to spawn its browser subprocess — calling it
in-process raises NotImplementedError. A separate process sidesteps the conflict (see services/site_service.py).
"""
from __future__ import annotations


def fetch_sitemap_urls(base_url: str, max_urls: int = 200) -> list[str]:
    """Fetch and parse sitemap.xml (handling a plain <urlset> or a <sitemapindex> of
    nested sitemaps, recursed one level deep) and return the page URLs found.

    Plain HTTP GET + XML parse — no Playwright/event-loop involved, so this is safe to
    call directly from Streamlit. Returns an empty list if no sitemap is found/parseable.
    """
    import requests
    import xml.etree.ElementTree as ET

    def _get_xml_root(url: str):
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return ET.fromstring(resp.content)

    def _local_tag(el) -> str:
        return el.tag.split("}")[-1] if "}" in el.tag else el.tag

    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    try:
        root = _get_xml_root(sitemap_url)
    except Exception:
        return []

    urls: list[str] = []
    root_tag = _local_tag(root)

    if root_tag == "sitemapindex":
        child_sitemaps = [
            loc.text.strip()
            for sm in root
            if _local_tag(sm) == "sitemap"
            for loc in sm
            if _local_tag(loc) == "loc" and loc.text
        ]
        for sm_url in child_sitemaps[:10]:  # cap nested sitemap fetches
            try:
                sub_root = _get_xml_root(sm_url)
                for entry in sub_root:
                    if _local_tag(entry) != "url":
                        continue
                    for loc in entry:
                        if _local_tag(loc) == "loc" and loc.text:
                            urls.append(loc.text.strip())
                            if len(urls) >= max_urls:
                                return urls
            except Exception:
                continue
    elif root_tag == "urlset":
        for entry in root:
            if _local_tag(entry) != "url":
                continue
            for loc in entry:
                if _local_tag(loc) == "loc" and loc.text:
                    urls.append(loc.text.strip())
                    if len(urls) >= max_urls:
                        return urls

    return urls


def crawl_site(url: str) -> dict:
    """Browse `url` and return a structural summary: title, nav links, headings, and forms.

    Returns an empty-ish dict with an "error" key if the site can't be reached.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=10000)

            title = page.title()

            nav_links = []
            for el in page.query_selector_all("nav a, header a, [role='navigation'] a"):
                text = (el.inner_text() or "").strip()
                if text and text not in nav_links:
                    nav_links.append(text)

            headings = []
            for el in page.query_selector_all("h1, h2, h3"):
                text = (el.inner_text() or "").strip()
                if text and text not in headings:
                    headings.append(text)

            forms = []
            for form in page.query_selector_all("form"):
                field_names = []
                for field in form.query_selector_all("input, textarea, select"):
                    label = (
                        field.get_attribute("placeholder")
                        or field.get_attribute("name")
                        or field.get_attribute("aria-label")
                        or field.get_attribute("type")
                        or ""
                    )
                    if label:
                        field_names.append(label)
                if field_names:
                    forms.append(field_names)

            buttons = []
            for el in page.query_selector_all("button, a.btn, [role='button']"):
                text = (el.inner_text() or "").strip()
                if text and text not in buttons:
                    buttons.append(text)

            browser.close()

            return {
                "url": url,
                "title": title,
                "nav_links": nav_links[:30],
                "headings": headings[:30],
                "forms": forms[:10],
                "buttons": buttons[:30],
            }
    except Exception as e:
        return {"url": url, "error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    import json
    import sys

    target_url = sys.argv[1]
    print(json.dumps(crawl_site(target_url)))
