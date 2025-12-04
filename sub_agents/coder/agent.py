"""Coder Agent module.

This module defines the Coder Agent, which is responsible for generating
build123d code based on design specifications.
"""

from google.adk.agents import LlmAgent
from tools.rag_tool import RAGTool
from tools.cad_tools import create_cad_model
from .prompt import SYSTEM_PROMPT
import os

def get_coder_agent(model_name: str = "gemini-3-pro-preview") -> LlmAgent:
    """Initialize and return the Coder Agent.

    Args:
        model_name (str): The name of the LLM model to use.

    Returns:
        LlmAgent: The configured Coder Agent instance.
    """
    rag_tool = RAGTool()

    return LlmAgent(
        model=model_name,
        name="CoderAgent",
        instruction=SYSTEM_PROMPT,
        tools=[rag_tool.query, create_cad_model]
    )
