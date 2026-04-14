import json
import re
from vertexai.generative_models import GenerativeModel
from agents.llm_client import OpenRouterClient


class MetisAdversarialGrader:
    ICON_BUDGETS = {
        "low": 1,
        "medium": 2,
        "high": 4,
    }
    RUBRIC = {
        "layout_clarity": "0-5 based on required section presence/order, heading consistency, and absence of wrappers/code fences.",
        "scanability": "0-5 based on short bullets (prefer <=24 words), concise sections, and low visual clutter.",
        "style_compliance": "0-5 based on adherence to style profile, concrete wording, and symbol restraint.",
        "factual_preservation": "0-5 based on preserving raw-report facts without unsupported new claims.",
        "signal_density": "0-5 based on actionable, high-information statements per section.",
    }

    RULES = [
        "Required sections must appear in order: Executive Snapshot, Key Signals, Risks / Unknowns, Recommended Actions, Sources.",
        "No code fences or decorative wrappers.",
        "Sources should contain http(s) links when available, otherwise explicit N/A.",
        "Flag malformed marker patterns and noisy formatting.",
        "Prefer concise bullets and avoid long narrative blocks.",
        "Penalize repeated/near-duplicate bullets across sections.",
        "Penalize generic filler statements that lack concrete technical detail.",
    ]

    def __init__(self):
        self.instructions = """
        You are the Metis Adversarial Grader.
        Challenge report readability and score it objectively.

        Score each dimension from 0.0 to 5.0:
        - layout_clarity
        - scanability
        - style_compliance
        - factual_preservation
        - signal_density

        Rules:
        - Be strict and concise.
        - Prioritize readability and clear structure over decorative style.
        - Flag fluff, overlong sections, unclear formatting, and style drift.
        - Penalize emoji or non-ASCII symbols for terminal compatibility.
        - Penalize bullets longer than 24 words unless unavoidable.
        - Recommend icon density as one of: low, medium, high.
        - Return JSON only.
        """
        self.openrouter = OpenRouterClient.from_env()
        self.model = None
        if self.openrouter is None:
            self.model = GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=self.instructions,
            )

    def _parse_result(self, text):
        default = {
            "layout_clarity": 3.0,
            "scanability": 3.0,
            "style_compliance": 3.0,
            "factual_preservation": 4.0,
            "signal_density": 3.0,
            "overall_score": 3.2,
            "icon_density": "medium",
            "feedback": ["Use shorter bullets and clearer sectioning."],
            "parse_status": "fallback_default",
        }
        candidates = [text]
        json_obj_match = re.search(r"\{[\s\S]*\}", text)
        if json_obj_match:
            candidates.append(json_obj_match.group(0))

        for candidate in candidates:
            try:
                data = json.loads(candidate)
                for key, fallback in default.items():
                    if key not in data:
                        data[key] = fallback
                if not isinstance(data.get("feedback"), list):
                    data["feedback"] = default["feedback"]
                data["parse_status"] = "parsed_json"
                return data
            except Exception:
                continue
        return default

    def grade(self, raw_report, styled_report, style_profile):
        rubric_block = "\n".join([f"- {k}: {v}" for k, v in self.RUBRIC.items()])
        rules_block = "\n".join([f"- {r}" for r in self.RULES])
        prompt = (
            "Score this styled report against the rubric and return JSON only.\n\n"
            "Threshold policy:\n"
            "- Target overall >= 4.0\n"
            "- Hard fails if factual_preservation < 4.5 or layout_clarity < 3.5\n\n"
            "Icon budget policy:\n"
            f"- low => max {self.ICON_BUDGETS['low']} marker bullets per section\n"
            f"- medium => max {self.ICON_BUDGETS['medium']} marker bullets per section\n"
            f"- high => max {self.ICON_BUDGETS['high']} marker bullets per section\n\n"
            "Rubric definitions:\n"
            f"{rubric_block}\n\n"
            "Readability rules:\n"
            f"{rules_block}\n\n"
            f"Style profile:\n{style_profile}\n\n"
            f"Raw report:\n{raw_report}\n\n"
            f"Styled report:\n{styled_report}\n\n"
            "JSON schema:\n"
            "{\n"
            '  "layout_clarity": number,\n'
            '  "scanability": number,\n'
            '  "style_compliance": number,\n'
            '  "factual_preservation": number,\n'
            '  "signal_density": number,\n'
            '  "overall_score": number,\n'
            '  "icon_density": "low|medium|high",\n'
            '  "feedback": ["short actionable feedback item", "..."]\n'
            "}"
        )
        if self.openrouter is not None:
            raw_result = self.openrouter.generate_text(self.instructions, prompt)
        else:
            raw_result = self.model.generate_content(prompt).text

        parsed = self._parse_result(raw_result)
        overall = float(parsed["overall_score"])
        factual = float(parsed["factual_preservation"])
        layout = float(parsed["layout_clarity"])
        parsed["pass"] = overall >= 4.0 and factual >= 4.5 and layout >= 3.5
        return parsed


def get_metis_grader():
    return MetisAdversarialGrader()
