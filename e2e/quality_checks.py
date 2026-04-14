import re


REQUIRED_SECTIONS = [
    "Executive Snapshot",
    "Key Signals",
    "Risks / Unknowns",
    "Recommended Actions",
    "Sources",
]


def _extract_sections(report_text):
    sections = {}
    current = None
    for raw in report_text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _section_bullets(lines):
    bullets = []
    for raw in lines:
        line = raw.strip()
        if line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets


def _count_words(text):
    return len([part for part in re.split(r"\s+", text.strip()) if part])


def _check_sources(lines):
    bullets = _section_bullets(lines)
    issues = []
    citation_lines = [b for b in bullets if re.match(r"^\[Citation \d+\]\(https?://[^)]+\)$", b)]
    na_lines = [b for b in bullets if b == "N/A"]
    other_lines = [b for b in bullets if b not in citation_lines and b not in na_lines]

    if citation_lines:
        if other_lines:
            issues.append("sources_contains_non_citation_lines")
        if na_lines:
            issues.append("sources_mixed_citations_and_na")
    else:
        if not na_lines:
            issues.append("sources_missing_citations_or_na")

    return {
        "citation_lines": citation_lines,
        "na_lines": na_lines,
        "issues": issues,
    }


def check_report(report_text):
    sections = _extract_sections(report_text)
    issues = []

    section_names = list(sections.keys())
    for required in REQUIRED_SECTIONS:
        if required not in sections:
            issues.append(f"missing_section:{required}")

    ordered_required = [name for name in section_names if name in REQUIRED_SECTIONS]
    if ordered_required != REQUIRED_SECTIONS[: len(ordered_required)]:
        issues.append("section_order_invalid")

    for section in REQUIRED_SECTIONS[:-1]:
        bullets = _section_bullets(sections.get(section, []))
        for bullet in bullets:
            if _count_words(bullet) > 24:
                issues.append(f"overlong_bullet:{section}")
                break

    sources_info = _check_sources(sections.get("Sources", []))
    issues.extend(sources_info["issues"])

    return {
        "sections_present": section_names,
        "sources": sources_info,
        "issues": issues,
        "passed": not issues,
    }
