"""Runner module for executing agent workflows.

This module initializes the necessary services and the ControlFlowAgent,
and provides a function to run the agent workflow.
"""

import asyncio
from typing import AsyncGenerator
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from sub_agents.control_flow.agent import ControlFlowAgent

# Initialize services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# Initialize ControlFlowAgent
control_flow_agent = ControlFlowAgent(session_service, memory_service)

async def run_agent(prompt: str, session_id: str, user_id: str = "user") -> AsyncGenerator[str, None]:
    """Executes the agent workflow via ControlFlowAgent.

    Args:
        prompt (str): The input prompt for the agent.
        session_id (str): The unique session identifier.
        user_id (str): The user identifier. Defaults to "user".

    Yields:
        str: Chunks of the agent's response.
    """
    async for chunk in control_flow_agent.run(prompt, session_id, user_id):
        yield chunk
