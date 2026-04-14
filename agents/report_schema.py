import json
import re
from urllib.parse import urlparse

REQUIRED_SECTIONS = [
    "Executive Snapshot",
    "Key Signals",
    "Risks / Unknowns",
    "Recommended Actions",
]


def _extract_json_object(text):
    candidates = [text]
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidates.append(match.group(0))

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def _normalize_section_items(items):
    normalized = []
    if not isinstance(items, list):
        return normalized
    for item in items:
        if not isinstance(item, str):
            continue
        cleaned = re.sub(r"^\s*[-*]\s*", "", item.strip())
        cleaned = re.sub(r"^\[(?:\-\>|!|\?|\*)\]\s*", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized[:5]


def _normalize_sources(sources):
    normalized = []
    if not isinstance(sources, list):
        return normalized
    for src in sources:
        if not isinstance(src, dict):
            continue
        title = str(src.get("title", "")).strip() or "Source"
        url = _clean_url(str(src.get("url", "")).strip()) or "N/A"
        if url != "N/A" and not re.match(r"^https?://", url, flags=re.IGNORECASE):
            url = "N/A"
        normalized.append({"title": title, "url": url})
    return normalized[:8]


def _title_from_url(url):
    try:
        host = urlparse(url).netloc.lower().strip()
        host = re.sub(r"^www\.", "", host)
        if host:
            return host
    except Exception:
        pass
    return "Source"


def _clean_url(url):
    if not isinstance(url, str):
        return "N/A"
    cleaned = url.strip().strip("'\"")
    while cleaned and cleaned[-1] in ['"', "'", ",", ";"]:
        cleaned = cleaned[:-1]
    if cleaned.endswith(")") and cleaned.count("(") < cleaned.count(")"):
        cleaned = cleaned[:-1]
    return cleaned


def _normalize_domain(url):
    try:
        host = urlparse(url).netloc.lower().strip()
        host = re.sub(r"^www\.", "", host)
        return host
    except Exception:
        return ""


def _is_host_like_title(title):
    t = (title or "").strip().lower()
    if not t:
        return True
    # e.g. "example.com"
    return bool(re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", t))


def _title_quality_score(title):
    t = (title or "").strip()
    if not t:
        return 0
    if _is_host_like_title(t):
        return 1
    # Prefer descriptive titles with multiple words.
    return 3 if len(t.split()) >= 2 else 2


def _extract_source_hints(text):
    hints = []
    if not isinstance(text, str) or not text.strip():
        return hints

    # Markdown links: [label](url)
    for m in re.finditer(r"\[([^\]]{1,120})\]\((https?://[^)\s]+)\)", text):
        title = m.group(1).strip()
        url = _clean_url(m.group(2).strip())
        hints.append({"title": title or _title_from_url(url), "url": url})

    # Bare URLs
    for m in re.finditer(r"(https?://[^\s)\]]+)", text):
        url = _clean_url(m.group(1).strip().rstrip(".,;"))
        hints.append({"title": _title_from_url(url), "url": url})
    return hints


def _dedupe_sources(sources):
    out = []
    seen_titles = set()
    url_index = {}
    for src in sources:
        title = str(src.get("title", "")).strip() or "Source"
        url = str(src.get("url", "")).strip() or "N/A"

        if url != "N/A":
            k = url.lower()
            if k in url_index:
                i = url_index[k]
                existing = out[i]
                # Keep the better, more descriptive title for the same URL.
                if _title_quality_score(title) > _title_quality_score(existing["title"]):
                    out[i] = {"title": title, "url": url}
                continue
            url_index[k] = len(out)
            out.append({"title": title, "url": url})
            continue

        # For N/A sources, dedupe by title only.
        tk = title.lower()
        if tk in seen_titles:
            continue
        seen_titles.add(tk)
        out.append({"title": title, "url": "N/A"})

    # Improve concrete source titles using related descriptive N/A entries by domain token match.
    # Example: concrete "gartner.com" + N/A "Gartner Hype Cycle..." => keep concrete URL with descriptive title.
    na_entries = [s for s in out if s.get("url") == "N/A"]
    concrete_entries = [s for s in out if s.get("url") != "N/A"]
    consumed_na_titles = set()
    improved_concrete = []
    for c in concrete_entries:
        title = c.get("title", "Source")
        url = c.get("url", "N/A")
        if _is_host_like_title(title):
            domain = _normalize_domain(url)
            token = domain.split(".")[0] if domain else ""
            if token:
                replacement = None
                for n in na_entries:
                    nt = (n.get("title") or "").strip()
                    if nt and token in nt.lower():
                        replacement = nt
                        consumed_na_titles.add(nt.lower())
                        break
                if replacement:
                    title = replacement
        improved_concrete.append({"title": title, "url": url})

    # Drop host-only N/A entries when same domain already has a concrete URL source.
    concrete_domains = {_normalize_domain(s["url"]) for s in improved_concrete if s.get("url")}
    filtered_na = []
    for s in na_entries:
        title = s.get("title", "")
        if title.lower() in consumed_na_titles:
            continue
        if _is_host_like_title(title) and title.lower() in concrete_domains:
            continue
        filtered_na.append(s)

    merged = improved_concrete + filtered_na
    return merged[:8]


def _build_source_trace(canonical_sources, hint_sources):
    """
    Internal traceability metadata for debugging source selection.
    """
    trace = []
    hint_map = {}
    for hint in hint_sources:
        url = hint.get("url", "N/A")
        if url != "N/A":
            hint_map.setdefault(url.lower(), []).append(hint.get("title", "Source"))

    for src in canonical_sources:
        url = src.get("url", "N/A")
        title = src.get("title", "Source")
        trace.append(
            {
                "url": url,
                "selected_title": title,
                "title_quality_score": _title_quality_score(title),
                "hint_titles": hint_map.get(url.lower(), []) if url != "N/A" else [],
            }
        )
    return trace


def _build_fallback_from_raw(raw_text):
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    words = " ".join(lines).split()

    def chunk(start, size):
        return " ".join(words[start:start + size]).strip() or "N/A"

    return {
        "executive_snapshot": [
            "Best-effort fallback was used because canonical parsing failed.",
            chunk(0, 40),
        ],
        "key_signals": [chunk(40, 35), chunk(75, 35), chunk(110, 35)],
        "risks_unknowns": [
            "Some generated content could not be normalized into the canonical schema.",
            chunk(145, 35),
        ],
        "recommended_actions": [
            "Re-run with a narrower topic if precision is needed.",
            "Review sources and replace N/A entries where possible.",
        ],
        "sources": [{"title": "Fallback", "url": "N/A"}],
        "parse_status": "fallback_from_raw",
    }


def parse_canonical_report(text, raw_fallback_text, source_hint_text=None):
    obj = _extract_json_object(text)
    if not isinstance(obj, dict):
        return _build_fallback_from_raw(raw_fallback_text)

    sections = obj.get("sections", {})
    sources = obj.get("sources", [])
    normalized_sources = _normalize_sources(sources)
    hint_sources = _normalize_sources(_extract_source_hints(source_hint_text or ""))
    combined_sources = _dedupe_sources(normalized_sources + hint_sources)

    # If model produced only N/A sources but hints have concrete URLs, prefer hinted URLs.
    all_na = combined_sources and all(s.get("url") == "N/A" for s in combined_sources)
    if all_na:
        hinted_urls = [s for s in hint_sources if s.get("url") != "N/A"]
        if hinted_urls:
            combined_sources = _dedupe_sources(hinted_urls + combined_sources)

    canonical = {
        "executive_snapshot": _normalize_section_items(sections.get("executive_snapshot", [])),
        "key_signals": _normalize_section_items(sections.get("key_signals", [])),
        "risks_unknowns": _normalize_section_items(sections.get("risks_unknowns", [])),
        "recommended_actions": _normalize_section_items(sections.get("recommended_actions", [])),
        "sources": combined_sources,
        "source_trace": _build_source_trace(combined_sources, hint_sources),
        "parse_status": "parsed_json",
    }

    # Ensure non-empty required sections.
    for key in ["executive_snapshot", "key_signals", "risks_unknowns", "recommended_actions"]:
        if not canonical[key]:
            canonical[key] = ["N/A"]
    if not canonical["sources"]:
        canonical["sources"] = [{"title": "Source", "url": "N/A"}]
    return canonical


def validate_canonical_report(canonical):
    issues = []
    if not isinstance(canonical, dict):
        return ["canonical_not_dict"]
    if not canonical.get("executive_snapshot"):
        issues.append("missing_executive_snapshot")
    if not canonical.get("key_signals"):
        issues.append("missing_key_signals")
    if not canonical.get("risks_unknowns"):
        issues.append("missing_risks_unknowns")
    if not canonical.get("recommended_actions"):
        issues.append("missing_recommended_actions")
    if not canonical.get("sources"):
        issues.append("missing_sources")
    return issues


def render_canonical_report_markdown(canonical):
    lines = []
    lines.append("## Executive Snapshot")
    lines.append("")
    for item in canonical["executive_snapshot"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Key Signals")
    lines.append("")
    for item in canonical["key_signals"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Risks / Unknowns")
    lines.append("")
    for item in canonical["risks_unknowns"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Recommended Actions")
    lines.append("")
    for item in canonical["recommended_actions"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    sources = canonical["sources"]
    concrete = [s for s in sources if s.get("url") != "N/A"]
    na_only = [s for s in sources if s.get("url") == "N/A"]

    # If we have concrete links, present only linked sources for cleaner output.
    display = concrete if concrete else na_only

    if concrete:
        for idx, src in enumerate(concrete, start=1):
            url = src["url"]
            lines.append(f"- [Citation {idx}]({url})")
    else:
        lines.append("- N/A")
    lines.append("")
    return "\n".join(lines)
