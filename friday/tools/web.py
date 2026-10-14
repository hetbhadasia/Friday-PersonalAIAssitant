"""
F.R.I.D.A.Y. V2 — Web Tools
============================
Real web search, multi-source global news briefings, safe page fetching, and visual world dashboard.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from friday.config import config
from friday.core.logging import get_logger
from friday.core.errors import NetworkError, ValidationError
from friday.services.web_search import search_web as real_search_web, format_results_for_llm
from friday.utils.network import validate_url, sanitize_search_query

logger = get_logger("web_tools")

DEFAULT_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'https://www.aljazeera.com/xml/rss/all.xml',
]


async def fetch_and_parse_feed(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Fetch and parse RSS XML feed safely."""
    try:
        response = await client.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Friday-AI/2.0'},
            timeout=config.resilience.HTTP_READ_TIMEOUT,
        )
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        domain = urlparse(url).netloc.replace("www.", "").split(".")[0].upper()

        feed_items = []
        items = root.findall(".//item")[:config.content.NEWS_ITEMS_PER_FEED]
        for item in items:
            title = item.findtext("title")
            description = item.findtext("description")
            link = item.findtext("link")

            if title:
                title = re.sub(r'<[^<]+?>', '', title).strip()
            if description:
                description = re.sub(r'<[^<]+?>', '', description).strip()

            if title and link:
                feed_items.append({
                    "source": domain,
                    "title": title,
                    "summary": (description[:200] + "...") if description else "",
                    "link": link,
                })
        return feed_items
    except Exception as exc:
        logger.warning("Feed fetch failed for %s: %s", url, exc)
        return []


def register(mcp):
    @mcp.tool()
    async def get_world_news() -> str:
        """
        Fetches the latest global headlines from major news outlets simultaneously.
        Use this when the user asks 'What's going on in the world?' or for recent events.
        """
        feeds = getattr(config.content, "NEWS_FEEDS", DEFAULT_FEEDS)

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=config.resilience.HTTP_TOTAL_TIMEOUT,
        ) as client:
            tasks = [fetch_and_parse_feed(client, url) for url in feeds]
            results_of_lists = await asyncio.gather(*tasks, return_exceptions=True)

            all_articles = []
            seen_titles = set()
            for sublist in results_of_lists:
                if isinstance(sublist, list):
                    for item in sublist:
                        # Deduplicate by normalized title
                        norm = re.sub(r'[^a-zA-Z0-9]', '', item["title"]).lower()
                        if norm not in seen_titles:
                            seen_titles.add(norm)
                            all_articles.append(item)

        if not all_articles:
            return "The global news grid is unresponsive, boss. I'm unable to pull live headlines at this moment."

        report = ["### GLOBAL NEWS BRIEFING (LIVE)\n"]
        max_articles = getattr(config.content, "NEWS_MAX_ARTICLES", 10)
        for entry in all_articles[:max_articles]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            if entry['summary']:
                report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    @mcp.tool()
    async def search_web(query: str) -> str:
        """
        Perform a live web search for recent information, documentation, articles, or real-time topics.
        Returns synthesized top web results.
        """
        try:
            results = await real_search_web(query)
            return format_results_for_llm(results)
        except Exception as exc:
            logger.error("Web search tool error: %s", exc)
            return f"I ran into an issue scanning the web for '{query}': {exc}"

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """
        Safely fetch and inspect text content from an external web page.
        Validates URL scheme and strips excess tags.
        """
        is_valid, reason = validate_url(url)
        if not is_valid:
            return f"Security check blocked URL fetch: {reason}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Friday-AI/2.0",
            "Accept": "text/html,text/plain",
        }

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=config.resilience.HTTP_READ_TIMEOUT,
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                text = response.text

                # Strip script, style, and HTML tags
                clean = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()

                max_chars = getattr(config.content, "FETCH_URL_MAX_CHARS", 4000)
                truncated = clean[:max_chars]
                return f"### Content from {url}\n\n{truncated}"
        except Exception as exc:
            logger.error("Error fetching URL %s: %s", url, exc)
            return f"Failed to retrieve content from {url}: {exc}"

    @mcp.tool()
    async def open_world_monitor() -> str:
        """
        Opens the World Monitor dashboard (worldmonitor.app) in the system's web browser.
        Use this when the user wants a visual overview of global events or a real-time map.
        """
        import webbrowser
        url = "https://worldmonitor.app/"

        try:
            webbrowser.open(url)
            return "Displaying the World Monitor on your primary screen now, boss."
        except Exception as e:
            return f"I'm unable to initialize the visual monitor: {str(e)}"