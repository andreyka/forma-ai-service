"""Designer Agent module.

This module defines the Designer Agent, which is responsible for creating
technical specifications for 3D models based on user requests.
"""

from google.adk.agents import LlmAgent
from tools.search_tools import SearchTools
from tools.rag_tool import RAGTool
from .prompt import SYSTEM_PROMPT
import os

def get_designer_agent(model_name: str = "gemini-3-pro-preview") -> LlmAgent:
    """Initialize and return the Designer Agent.

    Args:
        model_name (str): The name of the LLM model to use.

    Returns:
        LlmAgent: The configured Designer Agent instance.
    """
    search_tool = SearchTools()
    rag_tool = RAGTool()
    
    return LlmAgent(
        model=model_name,
        name="DesignerAgent",
        instruction=SYSTEM_PROMPT,
        tools=[search_tool.web_search, rag_tool.query, search_tool.fetch_page, search_tool.image_search]
    )
