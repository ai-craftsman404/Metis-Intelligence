from tools.search_tool import google_search

try:
    from adk import LlmAgent
except ModuleNotFoundError:
    LlmAgent = None


def get_researcher():
    if LlmAgent is None:
        raise RuntimeError("Optional dependency 'adk' is required to use the standalone researcher agent.")

    return LlmAgent(
        name="Researcher",
        instructions="""
        You are a research specialist.
        Your goal is to gather high-quality raw data on a given topic using your search tool.
        Be thorough and provide as much detail as possible in your response.
        """,
        tools=[google_search],
    )


researcher = get_researcher() if LlmAgent is not None else None
