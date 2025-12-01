import os
import asyncio
from typing import AsyncGenerator, Optional
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai.types import Content, Part

# Initialize services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

APP_NAME = "forma-ai-service"

from sub_agents.specification.agent import get_specification_agent
from sub_agents.code_generator.agent import get_code_generator_agent

# Initialize agents
spec_agent = get_specification_agent()
code_agent = get_code_generator_agent()

async def run_agent(prompt: str, session_id: str, user_id: str = "user") -> AsyncGenerator[str, None]:
    """
    Executes the agent workflow: Specification -> Code Generation.
    """
    
    # Create/Get session
    print(f"Runner: Ensuring session {session_id} exists for user {user_id}")
    session = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    
    if not session:
        print(f"Runner: Session not found (returned None). Creating new session...")
        await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        print("Runner: Session created.")
    else:
        print("Runner: Session found.")

    # 1. Run Specification Agent
    print("--- Running Specification Agent ---")
    runner_spec = Runner(
        agent=spec_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )
    
    spec_input = Content(parts=[Part(text=prompt)], role="user")
    spec_output = ""
    
    async for event in runner_spec.run_async(user_id=user_id, session_id=session_id, new_message=spec_input):
        if event.is_final_response() and event.content and event.content.parts:
            spec_output = event.content.parts[0].text
            # Yield intermediate progress
            yield f"Specification Generated:\n{spec_output[:100]}...\n"

    # 2. Run Code Generator Agent
    print("--- Running Code Generator Agent ---")
    # We pass the spec as the user input to the code generator
    runner_code = Runner(
        agent=code_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )
    
    code_input = Content(parts=[Part(text=f"Specification:\n{spec_output}")], role="user")
    
    async for event in runner_code.run_async(user_id=user_id, session_id=session_id, new_message=code_input):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
            yield final_response
