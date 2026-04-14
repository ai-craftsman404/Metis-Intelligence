try:
    from adk import LlmAgent
except ModuleNotFoundError:
    LlmAgent = None


def get_synthesizer():
    if LlmAgent is None:
        raise RuntimeError("Optional dependency 'adk' is required to use the standalone synthesizer agent.")

    return LlmAgent(
        name="Synthesizer",
        instructions="""
        You are a data synthesis expert.
        Your goal is to analyze raw research data and draft a well-structured, professional report.
        Identify key trends, interesting facts, and potential areas for further exploration.
        """,
        tools=[],  # No external tools, focuses on LLM-driven synthesis
    )


synthesizer = get_synthesizer() if LlmAgent is not None else None
