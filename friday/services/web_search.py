"""
F.R.I.D.A.Y. V2 — Web Search Service
=====================================
Real web search using DuckDuckGo HTML scraping.
No API key required.
"""

import re
import asyncio
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from friday.config import config
from friday.core.logging import get_logger, log_latency
from friday.core.errors import NetworkError, ValidationError
from friday.core.resilience import retry_async
from friday.utils.network import sanitize_search_query

logger = get_logger("web_search")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # domain

    def to_llm_string(self) -> str:
        return f"**[{self.source}]** {self.title}\n{self.snippet}\nURL: {self.url}"


async def search_web(query: str, max_results: int | None = None) -> list[SearchResult]:
    """
    Perform a real web search using DuckDuckGo HTML.
    
    Returns a list of SearchResult objects.
    Raises ValidationError for bad queries, NetworkError for connectivity issues.
    """
    if not query or not query.strip():
        raise ValidationError("Search query cannot be empty", field="query")

    query = sanitize_search_query(query)
    if len(query) < 2:
        raise ValidationError("Search query is too short", field="query")

    max_results = max_results or config.content.SEARCH_MAX_RESULTS

    try:
        results = await retry_async(
            _duckduckgo_search,
            query,
            max_results,
            max_retries=2,
            backoff_base=1.0,
            retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
            operation_name="web_search",
        )
        logger.info("Web search completed: query=%s results=%d", query[:50], len(results))
        return results

    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.error("Web search failed: %s", exc)
        raise NetworkError(f"Web search failed: {exc}", service="duckduckgo")
    except ValidationError:
        raise
    except Exception as exc:
        logger.error("Unexpected web search error: %s", exc)
        raise NetworkError(f"Web search error: {exc}", service="duckduckgo")


async def _duckduckgo_search(query: str, max_results: int) -> list[SearchResult]:
    """Scrape DuckDuckGo HTML search results."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(
            15.0,
            connect=config.resilience.HTTP_CONNECT_TIMEOUT,
            read=config.resilience.HTTP_READ_TIMEOUT,
            write=10.0,
            pool=5.0,
        ),
    ) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        html = response.text

    return _parse_ddg_html(html, max_results)


def _parse_ddg_html(html: str, max_results: int) -> list[SearchResult]:
    """Parse DuckDuckGo HTML results page."""
    results: list[SearchResult] = []

    # Extract result blocks — DuckDuckGo uses class="result__body"
    # Each result contains: result__a (title+url), result__snippet (description)
    
    # Pattern for result titles and URLs
    title_pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    snippet_pattern = re.compile(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    titles = title_pattern.findall(html)
    snippets = snippet_pattern.findall(html)

    for i, (raw_url, raw_title) in enumerate(titles[:max_results]):
        title = _clean_html(raw_title).strip()
        snippet = _clean_html(snippets[i]).strip() if i < len(snippets) else ""
        url = _extract_ddg_url(raw_url)

        if not title or not url:
            continue

        # Extract domain
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
        except Exception:
            domain = "unknown"

        results.append(SearchResult(
            title=title,
            url=url,
            snippet=snippet[:300],
            source=domain,
        ))

    return results


def _extract_ddg_url(raw_url: str) -> str:
    """Extract the actual URL from DuckDuckGo's redirect wrapper."""
    # DuckDuckGo wraps URLs like //duckduckgo.com/l/?uddg=<encoded_url>&...
    if "uddg=" in raw_url:
        from urllib.parse import unquote, parse_qs, urlparse
        parsed = urlparse(raw_url)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    
    # If it's a direct URL
    if raw_url.startswith("http"):
        return raw_url
    if raw_url.startswith("//"):
        return "https:" + raw_url

    return raw_url


def _clean_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def format_results_for_llm(results: list[SearchResult]) -> str:
    """Format search results into an LLM-friendly string."""
    if not results:
        return "No search results found."

    lines = [f"### Web Search Results ({len(results)} found)\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **[{r.source}]** {r.title}")
        if r.snippet:
            lines.append(f"   {r.snippet}")
        lines.append(f"   URL: {r.url}\n")

    return "\n".join(lines)
