from google.adk.agents import LlmAgent
from tools.search_tools import SearchTools
from tools.rag_tool import RAGTool
from .prompt import SYSTEM_PROMPT
import os

def get_designer_agent(model_name: str = "gemini-3-pro-preview") -> LlmAgent:
    search_tool = SearchTools()
    rag_tool = RAGTool()
    
    return LlmAgent(
        model=model_name,
        name="DesignerAgent",
        instruction=SYSTEM_PROMPT,
        tools=[search_tool.web_search, rag_tool.query, search_tool.fetch_page, search_tool.image_search]
    )
