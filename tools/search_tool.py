import json
import re
from html import unescape
from urllib import parse, request


def _extract_ddg_results(html_text):
    results = []
    anchor_pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    snippet_pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*>.*?</a>.*?<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    anchors = list(anchor_pattern.finditer(html_text))
    snippets = list(snippet_pattern.finditer(html_text))

    for idx, match in enumerate(anchors[:5]):
        href = unescape(match.group("href"))
        title = unescape(re.sub(r"<.*?>", "", match.group("title"))).strip()
        snippet = ""
        if idx < len(snippets):
            snippet = unescape(re.sub(r"<.*?>", "", snippets[idx].group("snippet"))).strip()

        # DuckDuckGo wraps outbound links as /l/?uddg=<urlencoded_target>
        parsed_href = parse.urlparse(href)
        if "duckduckgo.com" in parsed_href.netloc and parsed_href.path.startswith("/l/"):
            query = parse.parse_qs(parsed_href.query)
            href = parse.unquote(query.get("uddg", [href])[0])

        results.append(
            {
                "title": title,
                "snippet": snippet,
                "link": href,
                "source": "duckduckgo-web",
            }
        )
    return results


def _duckduckgo_search(query):
    ddg_params = parse.urlencode({"q": query})
    ddg_url = f"https://duckduckgo.com/html/?{ddg_params}"
    ddg_req = request.Request(
        url=ddg_url,
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 (Metis Intelligence)"},
    )
    with request.urlopen(ddg_req, timeout=20) as resp:
        html_text = resp.read().decode("utf-8", errors="ignore")

    results = _extract_ddg_results(html_text)
    if not results:
        return [
            {
                "title": f"No results for query: {query}",
                "snippet": "DuckDuckGo returned no parseable results.",
                "link": "",
                "source": "duckduckgo-web",
            }
        ]
    return results


def google_search(query: str) -> str:
    """
    Search for information on the public web.
    
    Args:
        query: The search query.
    
    Returns:
        A JSON string containing normalized search results.
    """
    try:
        return json.dumps(_duckduckgo_search(query))
    except Exception as exc:
        # Google Custom Search JSON API is closed to new customers, so this tool
        # now uses DuckDuckGo as the single live-search provider.
        return json.dumps(
            [
                {
                    "title": f"Search unavailable for query: {query}",
                    "snippet": str(exc),
                    "link": "",
                    "source": "search-error",
                }
            ]
        )

# Vertex AI ADK expectations: tools should be defined as callables or LangChain-style tools.
# ADK will automatically convert this to a tool definition.
