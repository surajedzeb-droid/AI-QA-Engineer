import json
import subprocess
import sys
import os
from requirement_parser.site_crawler import fetch_sitemap_urls
from chains.site_feature_chain import suggest_features

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def get_sitemap_pages(base_url: str) -> list[str]:
    """Return page URLs discovered from the target app's sitemap.xml (empty if none found)."""
    return fetch_sitemap_urls(base_url)


def _crawl_site_subprocess(url: str) -> dict:
    """Run the Playwright crawl in a separate process.

    Streamlit runs on Tornado, which forces asyncio's SelectorEventLoop policy on Windows; Playwright's
    sync API needs ProactorEventLoop to spawn its browser subprocess, so calling it in-process here would
    raise NotImplementedError. A fresh subprocess starts with the default (Proactor) policy, avoiding that.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "requirement_parser.site_crawler", url],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            return {"url": url, "error": result.stderr[-500:] or "Crawler subprocess failed"}
        return json.loads(result.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return {"url": url, "error": "Crawling timed out after 60 seconds"}
    except Exception as e:
        return {"url": url, "error": f"{type(e).__name__}: {e}"}


def analyze_target_site(url: str) -> dict:
    """Crawl `url` and return {"summary": dict, "suggestions": list, "error": str | None}."""
    summary = _crawl_site_subprocess(url)
    if summary.get("error"):
        return {"summary": summary, "suggestions": [], "error": summary["error"]}

    suggestions = suggest_features(summary)
    return {"summary": summary, "suggestions": suggestions, "error": None}
