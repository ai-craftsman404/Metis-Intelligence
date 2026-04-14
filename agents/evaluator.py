from vertexai.generative_models import GenerativeModel
from agents.llm_client import OpenRouterClient

# Metis Evaluator: Specialized in formatting, styling, and quality control.
class MetisEvaluator:
    def __init__(self):
        self.instructions = """
        You are the Metis Output Stylist.
        Your job is to convert technical content into a strict canonical JSON report schema.

        Core rules:
        1. Keep technical facts intact; do not invent claims.
        2. Prefer short, specific bullets over long prose.
        3. Keep tone professional and practical; avoid fluffy language.
        4. Output JSON only, no markdown fences, no commentary.
        5. Use concrete source URLs when available, otherwise N/A.
        6. Avoid generic filler bullets (e.g., "This is important", "There is a trend").
        """
        self.openrouter = OpenRouterClient.from_env()
        self.model = None
        if self.openrouter is None:
            self.model = GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=self.instructions
            )

    def evaluate(
        self,
        report_text,
        style_profile,
        grader_feedback=None,
        allow_na_sources=False,
        marker_budget_per_section=2,
    ):
        """
        Refine and style the synthesis report.
        """
        feedback_block = ""
        if grader_feedback:
            feedback_lines = "\n".join(f"- {item}" for item in grader_feedback)
            feedback_block = (
                "\n\nAddress the following grader feedback:\n"
                f"{feedback_lines}\n"
            )

        prompt = (
            "Rewrite the report into canonical JSON using the constraints below.\n\n"
            f"Style profile:\n{style_profile}\n\n"
            "Hard constraints:\n"
            "- Return JSON only with this exact top-level shape:\n"
            "  {\n"
            '    "sections": {\n'
            '      "executive_snapshot": [string, ...],\n'
            '      "key_signals": [string, ...],\n'
            '      "risks_unknowns": [string, ...],\n'
            '      "recommended_actions": [string, ...]\n'
            "    },\n"
            '    "sources": [{"title": string, "url": string}, ...]\n'
            "  }\n"
            "- Max 5 bullets per section.\n"
            "- Keep bullets concise (target <= 24 words per bullet).\n"
            "- Start bullets with concrete technical nouns/verbs, not generic openers.\n"
            "- No markdown, headings, bullets, prose wrappers, or code fences.\n"
            "- If a source link is unavailable or unverifiable, write 'N/A' for that source link.\n"
            "- No mythology metaphors or theatrical language.\n"
            f"- Citation fallback mode: {'ENABLED (use N/A for missing links)' if allow_na_sources else 'DISABLED (prefer concrete URLs)'}.\n"
            f"{feedback_block}\n\n"
            f"Raw report:\n{report_text}"
        )
        if self.openrouter is not None:
            return self.openrouter.generate_text(self.instructions, prompt)
        response = self.model.generate_content(prompt)
        return response.text

def get_metis_evaluator():
    return MetisEvaluator()
