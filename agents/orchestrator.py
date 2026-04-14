import json
import logging
import os
import re
import sys
from vertexai.generative_models import GenerativeModel, Tool, Part, FunctionDeclaration
from agents.llm_client import OpenRouterClient
from agents.report_schema import parse_canonical_report, render_canonical_report_markdown, validate_canonical_report
from tools.search_tool import google_search

# Domain-specific personas and instructions
DOMAIN_PERSONAS = {
    "1": ("AI Infrastructure", "Focus on technical signals related to GPU optimization, LLM training bottlenecks, and distributed computing."),
    "2": ("Cybersecurity & Zero Trust", "Look for breakout technical whitepapers on post-quantum cryptography, threat intelligence patterns, and zero-trust architectures."),
    "3": ("Edge Computing", "Identify high-signal trends in IoT sensor fusion, 5G/6G latency optimization, and distributed edge processing."),
    "4": ("Sustainable Tech", "Search for technical developments in carbon-aware computing, energy-efficient data center cooling, and green hardware."),
    "5": ("FinTech & DeFi", "Focus on technical breakthroughs in regulatory technology (RegTech), decentralized finance protocols, and asset tokenization."),
    "6": ("BioTech & HealthTech", "Identify signals in computational genomics, AI-driven drug discovery, and personalized medicine infrastructure."),
    "7": ("AI Robotics", "Focus on technical trends in autonomous systems, human-robot interaction (HRI) models, and edge-native robotic control."),
    "8": ("Crypto and Digital Currency", "Look for developments in Web3 protocols, Central Bank Digital Currencies (CBDCs), and layer-2 scaling solutions."),
    "9": ("Custom Domain", "Gather high-signal data for a custom domain provided by the user.")
}

def get_orchestrator_instructions(domain_id, custom_domain=None):
    domain_name, focus_area = DOMAIN_PERSONAS.get(domain_id, DOMAIN_PERSONAS["9"])
    if domain_id == "9" and custom_domain:
        domain_name = custom_domain
        focus_area = f"Gather high-signal technical data specifically for the domain: {custom_domain}."
    
    return f"""
    You are a high-level Metis Intelligence Project Manager specializing in {domain_name}.
    Your goal is to coordinate a high-signal research and synthesis process, named after Metis, the Titaness of Wisdom and Cunning Intelligence.
    
    Current Domain Focus: {focus_area}
    
    Workflow:
    1. Research: Search for 'High-Signal' data on {domain_name} breakout trends from the last 24-48 hours.
    2. Synthesis: Analyze the raw results and draft a professional, technical intelligence report.
    
    Ensure the final report reflects your expert persona in {domain_name} and provides actionable technical intelligence.
    """

# Initialize the Vertex AI Search Tool using FunctionDeclaration
search_func = FunctionDeclaration(
    name="google_search",
    description="Search for technical information on the web.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."}
        },
        "required": ["query"]
    }
)

search_tool = Tool(function_declarations=[search_func])

from agents.evaluator import get_metis_evaluator
from agents.grader import get_metis_grader

logger = logging.getLogger(__name__)
if not logger.handlers:
    log_level_name = os.getenv("METIS_LOG_LEVEL", "WARNING").upper()
    log_level = getattr(logging, log_level_name, logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

STYLE_PROFILES = {
    "1": "Audience: engineering leaders. Icon density: low. Emphasize architecture, performance, throughput metrics.",
    "2": "Audience: security teams. Icon density: medium. Emphasize risks, exposure, mitigations, and incident urgency.",
    "3": "Audience: edge platform teams. Icon density: low. Emphasize latency, device constraints, and deployment tradeoffs.",
    "4": "Audience: sustainability and infra teams. Icon density: low. Emphasize efficiency, carbon, and infra impact.",
    "5": "Audience: fintech operators. Icon density: medium. Emphasize compliance, risk, and technical execution.",
    "6": "Audience: health/bio engineering teams. Icon density: low. Emphasize reliability, safety, and evidence quality.",
    "7": "Audience: robotics teams. Icon density: medium. Emphasize control loops, perception stacks, and real-world constraints.",
    "8": "Audience: crypto infra teams. Icon density: medium. Emphasize protocol, security, and scaling implications.",
    "9": "Audience: general technical stakeholders. Icon density: medium. Emphasize clear concise formatting and actionability.",
}

ICON_BUDGETS = {
    "low": 1,
    "medium": 2,
    "high": 4,
}


def get_style_profile(domain_id, custom_domain=None):
    base = STYLE_PROFILES.get(domain_id, STYLE_PROFILES["9"])
    if domain_id == "9" and custom_domain:
        lowered = custom_domain.lower()
        if any(x in lowered for x in ["security", "cyber", "threat"]):
            base = STYLE_PROFILES["2"]
        elif any(x in lowered for x in ["infra", "mlops", "gpu", "llm"]):
            base = STYLE_PROFILES["1"]
    return base


def _apply_visual_mode(text, mode):
    """
    Deterministic terminal glyph mapping by section.
    mode: ascii | utf8 | emoji
    """
    if mode not in {"utf8", "emoji"}:
        return text

    if mode == "emoji":
        heading_map = {
            "## Executive Snapshot": "## 📌 Executive Snapshot",
            "## Key Signals": "## 🔎 Key Signals",
            "## Risks / Unknowns": "## ⚠️ Risks / Unknowns",
            "## Recommended Actions": "## ✅ Recommended Actions",
            "## Sources": "## 🔗 Sources",
        }
        bullet_map = {
            "executive snapshot": "🧭",
            "key signals": "🔹",
            "risks / unknowns": "⚠️",
            "recommended actions": "✅",
            "sources": "🔗",
        }
    else:
        heading_map = {
            "## Executive Snapshot": "## • Executive Snapshot",
            "## Key Signals": "## > Key Signals",
            "## Risks / Unknowns": "## ! Risks / Unknowns",
            "## Recommended Actions": "## -> Recommended Actions",
            "## Sources": "## # Sources",
        }
        bullet_map = {
            "executive snapshot": "•",
            "key signals": ">",
            "risks / unknowns": "!",
            "recommended actions": "->",
            "sources": "#",
        }

    lines = text.splitlines()
    updated = []
    current_section = ""

    for line in lines:
        stripped = line.strip()
        if stripped in heading_map:
            line = heading_map[stripped]
            current_section = stripped[3:].strip().lower()
            updated.append(line)
            continue

        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            updated.append(line)
            continue

        if re.match(r"^\s*-\s+", line):
            glyph = bullet_map.get(current_section)
            if glyph and not re.match(rf"^\s*-\s+{re.escape(glyph)}\s+", line):
                line = re.sub(r"^\s*-\s+", f"- {glyph} ", line, count=1)

        updated.append(line)

    return "\n".join(updated)


def _is_utf8_stdout():
    enc = (getattr(sys.stdout, "encoding", None) or "").lower()
    if "utf-8" in enc or "utf8" in enc:
        return True
    # Common Windows UTF-8 code page env fallback.
    if os.getenv("PYTHONUTF8") == "1":
        return True
    return False


def _is_likely_modern_terminal():
    # Windows Terminal sets WT_SESSION. iTerm and most modern Unix terminals expose TERM.
    if os.getenv("WT_SESSION"):
        return True
    term_program = (os.getenv("TERM_PROGRAM") or "").lower()
    if term_program in {"iterm.app", "apple_terminal", "vscode"}:
        return True
    term = (os.getenv("TERM") or "").lower()
    return any(x in term for x in ["xterm", "screen", "tmux", "vt100", "ansi", "rxvt"])


def _resolve_glyph_mode():
    requested = os.getenv("METIS_GLYPH_MODE", "ascii").strip().lower()
    if requested not in {"ascii", "utf8", "emoji"}:
        requested = "ascii"

    # Always safe.
    if requested == "ascii":
        return "ascii"

    # utf8/emoji require UTF-8 capable output to avoid degraded rendering.
    if not _is_utf8_stdout():
        return "ascii"

    # utf8 symbols are allowed once UTF-8 capability is present.
    if requested == "utf8":
        return "utf8"

    # emoji requires explicit manual opt-in + likely modern terminal.
    allow_emoji = os.getenv("METIS_ENABLE_EMOJI", "0").strip().lower() in {"1", "true", "yes", "on"}
    if allow_emoji and _is_likely_modern_terminal():
        return "emoji"

    # If emoji requested but not explicitly allowed, degrade gracefully to utf8 symbols.
    return "utf8"


def to_terminal_safe(text):
    glyph_mode = _resolve_glyph_mode()
    if glyph_mode in {"utf8", "emoji"}:
        return _apply_visual_mode(text, glyph_mode)
    if os.name == "nt":
        return text.encode("cp1252", errors="ignore").decode("cp1252")
    return text


def sanitize_markers(report_text):
    """
    Subtask 1: fix known malformed marker tokens on list-like lines only.
    """
    lines = report_text.splitlines()
    cleaned = []
    marker_fixes = {
        r"(\[\!\])\.(?=\s|\*|$)": r"\1",
        r"(\[\*\])\.(?=\s|\*|$)": r"\1",
        r"(\[\?\])\.(?=\s|\*|$)": r"\1",
        r"(\[\-\>\])\.(?=\s|\*|$)": r"\1",
    }
    list_line_prefix = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")
    marker_line_prefix = re.compile(r"^\s*\[(?:!|\*|\?|\-\>)\]")

    for line in lines:
        updated = line
        if list_line_prefix.match(updated) or marker_line_prefix.match(updated):
            for pattern, replacement in marker_fixes.items():
                updated = re.sub(pattern, replacement, updated)
            if marker_line_prefix.match(updated):
                updated = f"- {updated.lstrip()}"
            # Normalize bullet style to "-" for cleaner terminal readability.
            updated = re.sub(r"^\s*[\*]\s+", "- ", updated)
        cleaned.append(updated)
    return "\n".join(cleaned)


def normalize_marker_bullets(report_text):
    """
    Convert noisy symbolic marker bullets into clean semantic bullet labels.
    """
    lines = report_text.splitlines()
    cleaned = []
    marker_map = {
        "[->]": "Action:",
        "[!]": "Signal:",
        "[?]": "Risk:",
        "[*]": "Note:",
    }

    for line in lines:
        # Normalize source-footnote style first: [^1]: Title. "Quote", URL
        footnote = re.match(r"^\s*[-*]?\s*\[\^[^\]]+\]:\s*(.+)$", line)
        if footnote:
            content = footnote.group(1).strip()
            cleaned.append(f"- {content}")
            continue

        marker_match = re.match(r"^\s*[-*]\s+(\[(?:\-\>|!|\?|\*)\])\s*(.+)$", line)
        if marker_match:
            marker = marker_match.group(1)
            content = marker_match.group(2).strip()
            label = marker_map.get(marker, "")
            if label:
                cleaned.append(f"- {label} {content}")
            else:
                cleaned.append(f"- {content}")
            continue

        # Handle bare marker lines like: [->] text
        bare_marker_match = re.match(r"^\s*(\[(?:\-\>|!|\?|\*)\])\s*(.+)$", line)
        if bare_marker_match:
            marker = bare_marker_match.group(1)
            content = bare_marker_match.group(2).strip()
            label = marker_map.get(marker, "")
            if label:
                cleaned.append(f"- {label} {content}")
            else:
                cleaned.append(f"- {content}")
            continue

        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_sections(report_text):
    """
    Subtask 2: remove extra wrappers and enforce consistent section heading labels.
    """
    text = report_text
    text = re.sub(r"^\s*```(?:markdown)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    text = re.sub(r"^#\s+Metis Intelligence Report.*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+Executive Summary\b", "## Executive Snapshot", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^##\s+Actionable Wisdom\b", "## Recommended Actions", text, flags=re.IGNORECASE | re.MULTILINE)
    return text


def normalize_citations(report_text):
    """
    Subtask 3: normalize source placeholders to explicit N/A fallback.
    """
    text = report_text
    text = text.replace("[Link Placeholder]", "N/A")
    text = text.replace("[-> examples]", "N/A")
    text = re.sub(r"\[\-\>\]\s*$", "N/A", text, flags=re.MULTILINE)
    return text


def normalize_sources_bullets(report_text):
    """
    Ensure Sources section uses bullet lines for deterministic readability.
    """
    marker = "## Sources"
    idx = report_text.find(marker)
    if idx < 0:
        return report_text

    head = report_text[:idx]
    tail = report_text[idx:]
    lines = tail.splitlines()
    if not lines:
        return report_text

    normalized = [lines[0]]
    for ln in lines[1:]:
        stripped = ln.strip()
        if not stripped:
            normalized.append("")
            continue
        if stripped.startswith("* ") or stripped.startswith("- "):
            normalized.append(stripped.replace("* ", "- ", 1))
            continue
        # Convert numbered or plain source lines to bullet lines.
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        normalized.append(f"- {stripped}")

    return head + "\n".join(normalized)


def canonicalize_bullet_style(report_text):
    """
    Canonicalize bullets to '-' and reduce spacing noise in list lines.
    """
    lines = report_text.splitlines()
    cleaned = []
    for line in lines:
        if re.match(r"^\s*\*\s+", line):
            line = re.sub(r"^\s*\*\s+", "- ", line)
        if re.match(r"^\s*-\s{2,}", line):
            line = re.sub(r"^\s*-\s+", "- ", line)
        cleaned.append(line)
    return "\n".join(cleaned)


def _truncate_words(text, max_words):
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(" ,;:") + " ..."


def enforce_bullet_length_limit(report_text, max_words=24):
    """
    Deterministically cap bullet length for scanability.
    """
    lines = report_text.splitlines()
    out = []
    for line in lines:
        m = re.match(r"^(\s*-\s+)(.+)$", line)
        if not m:
            out.append(line)
            continue
        prefix, content = m.group(1), m.group(2).strip()
        out.append(prefix + _truncate_words(content, max_words))
    return "\n".join(out)


def _normalize_for_similarity(text):
    t = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t.lower())
    tokens = [w for w in t.split() if len(w) > 2]
    return set(tokens)


def suppress_near_duplicate_bullets(report_text, threshold=0.72):
    """
    Remove near-duplicate bullets within each section to keep signal density high.
    """
    lines = report_text.splitlines()
    out = []
    current_section = None
    section_bullets = {}

    def is_duplicate(section, content):
        tokens = _normalize_for_similarity(content)
        if not tokens:
            return False
        existing = section_bullets.setdefault(section, [])
        for seen_tokens in existing:
            overlap = len(tokens & seen_tokens)
            union = len(tokens | seen_tokens) or 1
            jaccard = overlap / union
            if jaccard >= threshold:
                return True
        existing.append(tokens)
        return False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            out.append(line)
            continue
        m = re.match(r"^(\s*-\s+)(.+)$", line)
        if m and current_section:
            content = m.group(2).strip()
            if is_duplicate(current_section, content):
                continue
        out.append(line)
    return "\n".join(out)


def reduce_markdown_emphasis_noise(report_text):
    """
    Remove decorative bold/italic emphasis markers while preserving list markers.
    """
    text = report_text
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!^)\*([^*\n]+)\*(?!\s*$)", r"\1", text, flags=re.MULTILINE)
    return text


def whitespace_wrap_cleanup(report_text):
    """
    Subtask 4: whitespace cleanup for terminal readability.
    """
    text = report_text
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def final_guard_check(report_text):
    """
    Subtask 5: final output guard. Return (ok, reason).
    """
    required_sections = [
        "## Executive Snapshot",
        "## Key Signals",
        "## Risks / Unknowns",
        "## Recommended Actions",
        "## Sources",
    ]
    for section in required_sections:
        if section not in report_text:
            return False, f"missing_section:{section}"
    if re.search(r"\[\!\]\.(?=\s|\*|$)", report_text):
        return False, "odd_marker_remaining"
    if "Link Placeholder" in report_text or "[-> examples]" in report_text:
        return False, "placeholder_remaining"
    return True, "ok"


def build_structured_fallback(raw_text):
    """
    Deterministic safe fallback preserving required output structure.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    words = " ".join(lines).split()

    def chunk(start, size):
        return " ".join(words[start:start + size]).strip()

    c1 = chunk(0, 80) or "N/A"
    c2 = chunk(80, 120) or c1
    c3 = chunk(200, 120) or c2
    c4 = chunk(320, 120) or c3

    return (
        "## Executive Snapshot\n\n"
        "- Best-effort fallback was applied after formatting validation failed.\n"
        f"- Core content preview: {c1}\n"
        f"- Additional context: {c2}\n\n"
        "## Key Signals\n\n"
        f"- {c2}\n"
        f"- {c3}\n"
        f"- {c4}\n\n"
        "## Risks / Unknowns\n\n"
        "- Some stylistic constraints were not satisfied in the generated draft.\n"
        "- Source links may be incomplete in fallback mode.\n"
        f"- {c3}\n\n"
        "## Recommended Actions\n\n"
        "- Re-run the same domain query for an alternate draft.\n"
        "- If needed, narrow the query/topic scope to improve formatting consistency.\n\n"
        "## Sources\n\n"
        "- N/A\n"
    )


def apply_final_cleanup_pipeline(report_text, fallback_text):
    text = sanitize_markers(report_text)
    text = normalize_marker_bullets(text)
    text = normalize_sections(text)
    text = normalize_citations(text)
    text = normalize_sources_bullets(text)
    text = canonicalize_bullet_style(text)
    text = suppress_near_duplicate_bullets(text)
    text = enforce_bullet_length_limit(text, max_words=24)
    text = reduce_markdown_emphasis_noise(text)
    text = whitespace_wrap_cleanup(text)
    ok, reason = final_guard_check(text)
    if not ok:
        logger.info("metis_cleanup_guard status=fallback_plain_report reason=%s", reason)
        return build_structured_fallback(fallback_text)
    logger.info("metis_cleanup_guard status=pass")
    return text


def lint_output_formatting(report_text):
    issues = []
    if re.search(r"\[\!\]\.(?=\s|\*|$)", report_text):
        issues.append("odd_list_marker_[!]. detected")
    if "Link Placeholder" in report_text:
        issues.append("placeholder_source_link detected")
    if "[-> examples]" in report_text:
        issues.append("placeholder_action_link detected")
    if re.search(r"\[\-\>\]\s*$", report_text, flags=re.MULTILINE):
        issues.append("dangling_[->]_token detected")
    if re.search(r"^-\s+(\S+\s+){24,}\S+", report_text, flags=re.MULTILINE):
        issues.append("overlong_bullet_detected")

    sources_idx = report_text.lower().find("## sources")
    if sources_idx >= 0:
        sources_section = report_text[sources_idx:]
        has_http_links = "http://" in sources_section or "https://" in sources_section
        has_na_fallback = re.search(r"\bN/?A\b", sources_section, flags=re.IGNORECASE) is not None
        if not has_http_links and not has_na_fallback:
            issues.append("sources_section_has_no_http_links")
        source_lines = [ln.strip() for ln in sources_section.splitlines() if ln.strip().startswith("- ")]
        if source_lines:
            na_count = sum(1 for ln in source_lines if re.search(r":\s*N/?A\s*$", ln, flags=re.IGNORECASE))
            if na_count == len(source_lines):
                issues.append("sources_all_na")

    return issues


def lint_marker_budget(report_text, marker_budget_per_section):
    """
    Enforce max marker-prefixed bullets per section.
    Marker bullet example: '- [!] text'
    """
    issues = []
    current_section = "root"
    marker_counts = {}

    for line in report_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            marker_counts.setdefault(current_section, 0)
            continue

        if re.match(r"^[-*]\s+\[(?:!|\*|\?|\-\>)\]", stripped):
            marker_counts[current_section] = marker_counts.get(current_section, 0) + 1

    for section, count in marker_counts.items():
        if count > marker_budget_per_section:
            issues.append(
                f"marker_budget_exceeded section={section} count={count} budget={marker_budget_per_section}"
            )
    return issues

class MetisOrchestrator:
    def __init__(self, domain_id, custom_domain=None):
        self.domain_id = domain_id
        self.custom_domain = custom_domain
        self.instructions = get_orchestrator_instructions(domain_id, custom_domain)
        self.openrouter = OpenRouterClient.from_env()
        self.model = None
        if self.openrouter is None:
            self.model = GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=self.instructions
            )
        self.evaluator = get_metis_evaluator()
        self.grader = get_metis_grader()
        self.style_profile = get_style_profile(domain_id, custom_domain)
        self.last_icon_density = "medium"

    def ask(self, prompt):
        """
        Ask Metis to discover, synthesize, and evaluate wisdom.
        """
        if self.openrouter is not None:
            # Keep tool behavior consistent by injecting the local search tool output into the prompt.
            tool_payload = google_search(prompt)
            source_hint_text = tool_payload
            openrouter_prompt = (
                f"{prompt}\n\n"
                "Use the following JSON search results as your research input data:\n"
                f"{tool_payload}\n\n"
                "If the input data is limited, explicitly call that out in the report."
            )
            raw_report = self.openrouter.generate_text(self.instructions, openrouter_prompt)
        else:
            # Use the same deterministic search-injected prompt flow as the
            # OpenRouter path. This avoids fragile Vertex tool-call turn
            # handling while preserving live web research behavior.
            tool_payload = google_search(prompt)
            source_hint_text = tool_payload
            vertex_prompt = (
                f"{prompt}\n\n"
                "Use the following JSON search results as your research input data:\n"
                f"{tool_payload}\n\n"
                "If the input data is limited, explicitly call that out in the report."
            )
            raw_report = self.model.generate_content(vertex_prompt).text

        # Step 2: Style + adversarial grading loop (best effort, max 3 retries).
        best_report = raw_report
        best_score = -1.0
        best_lint_count = 10**9
        feedback = None
        icon_density = "medium"
        max_retries = 3

        for attempt in range(max_retries + 1):
            profile_with_icon = f"{self.style_profile} Grader-requested icon density: {icon_density}."
            allow_na_sources = attempt >= 2
            marker_budget_per_section = ICON_BUDGETS.get(icon_density, ICON_BUDGETS["medium"])
            try:
                candidate_json = self.evaluator.evaluate(
                    raw_report,
                    profile_with_icon,
                    feedback,
                    allow_na_sources=allow_na_sources,
                    marker_budget_per_section=marker_budget_per_section,
                )
                candidate_canonical = parse_canonical_report(
                    candidate_json,
                    raw_report,
                    source_hint_text=source_hint_text or raw_report,
                )
                schema_issues = validate_canonical_report(candidate_canonical)
                candidate = render_canonical_report_markdown(candidate_canonical)
                grade = self.grader.grade(raw_report, candidate, profile_with_icon)
                score = float(grade.get("overall_score", 0.0))
                lint_issues = lint_output_formatting(candidate)
                budget_issues = lint_marker_budget(candidate, marker_budget_per_section)
                lint_issues.extend(budget_issues)
                lint_issues.extend([f"schema_issue:{issue}" for issue in schema_issues])

                if score > best_score or (score == best_score and len(lint_issues) < best_lint_count):
                    best_score = score
                    best_report = candidate
                    best_lint_count = len(lint_issues)

                icon_density = grade.get("icon_density", icon_density)
                self.last_icon_density = icon_density
                feedback = list(grade.get("feedback", []))
                if lint_issues:
                    feedback.extend([f"Fix formatting issue: {issue}" for issue in lint_issues])

                logger.info(
                    "metis_grade attempt=%s score=%.2f pass=%s layout=%.2f factual=%.2f retries_left=%s icon_density=%s marker_budget=%s parse_status=%s schema_parse_status=%s allow_na_sources=%s lint_issues=%s feedback_count=%s",
                    attempt,
                    score,
                    grade.get("pass", False),
                    float(grade.get("layout_clarity", 0.0)),
                    float(grade.get("factual_preservation", 0.0)),
                    max_retries - attempt,
                    icon_density,
                    marker_budget_per_section,
                    grade.get("parse_status", "unknown"),
                    candidate_canonical.get("parse_status", "unknown"),
                    allow_na_sources,
                    "|".join(lint_issues) if lint_issues else "none",
                    len(feedback),
                )

                if grade.get("pass", False) and not lint_issues:
                    logger.info("metis_quality_gate status=pass attempt=%s", attempt)
                    final_text = apply_final_cleanup_pipeline(candidate, raw_report)
                    return to_terminal_safe(final_text)
                if grade.get("pass", False) and lint_issues:
                    logger.info(
                        "metis_quality_gate status=retry_due_to_lint attempt=%s issues=%s",
                        attempt,
                        "|".join(lint_issues),
                    )
            except Exception as exc:
                logger.exception("metis_style_pipeline_error attempt=%s error=%s", attempt, exc)

        # Threshold override after retries: return best styled attempt.
        if best_score >= 0:
            self.last_icon_density = icon_density
            final_text = apply_final_cleanup_pipeline(best_report, raw_report)
            final_lint = lint_output_formatting(final_text)
            logger.info(
                "metis_grade threshold_override best_score=%.2f final_lint_issues=%s",
                best_score,
                "|".join(final_lint) if final_lint else "none",
            )
            return to_terminal_safe(final_text)

        # Failure behavior: fallback plain report.
        logger.info("metis_quality_gate status=fallback_plain_report reason=no_successful_styled_candidate")
        return to_terminal_safe(apply_final_cleanup_pipeline(raw_report, raw_report))

def get_metis_orchestrator(domain_id, custom_domain=None):
    return MetisOrchestrator(domain_id, custom_domain)
