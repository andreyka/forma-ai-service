"""API endpoints for the Agent-to-Agent (A2A) protocol.

This module defines the FastAPI router for handling A2A messages,
task management, and agent capabilities discovery.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import Dict
from a2a.models import (
    SendMessageRequest, Task, TaskStatus, TaskState, Message, Role, Part, FilePart, AgentCard
)
from a2a.task_manager import TaskManager
from runner import run_agent
import os

router = APIRouter()
task_manager = TaskManager()

async def process_a2a_task(task_id: str, prompt: str, context_id: str) -> None:
    """Process an A2A task in the background.

    Args:
        task_id (str): The unique identifier for the task.
        prompt (str): The input prompt from the user/agent.
        context_id (str): The context or session ID.
    """
    print(f"Processing A2A task {task_id} with prompt: {prompt}")
    task_manager.update_task_status(task_id, TaskState.WORKING)
    
    # Set the task ID in the context variable so tools can use it
    from tools.cad_tools import task_id_var
    token = task_id_var.set(task_id)
    
    try:
        final_response = ""
        # Execute the agent workflow via Runner
        async for response_chunk in run_agent(prompt=prompt, session_id=context_id):
            final_response = response_chunk
            # Optional: Update task with intermediate progress if supported
            # task_manager.update_task_status(task_id, TaskState.WORKING, Message(role=Role.AGENT, parts=[Part(text=response_chunk)]))

        # Check for generated files in outputs/ matching the task ID
        # This is robust and doesn't rely on the agent's text output
        stl_filename = None
        step_filename = None
        
        for filename in os.listdir("outputs"):
            if filename.startswith(task_id):
                if filename.endswith(".stl"):
                    stl_filename = filename
                elif filename.endswith(".step"):
                    step_filename = filename

        parts = [Part(text=final_response)]
        
        if stl_filename:
             parts.append(Part(file=FilePart(
                    file_with_uri=f"/download/{stl_filename}",
                    name=stl_filename,
                    media_type="model/stl"
                )))
        
        if step_filename:
             parts.append(Part(file=FilePart(
                    file_with_uri=f"/download/{step_filename}",
                    name=step_filename,
                    media_type="model/step"
                )))

        response_message = Message(
            role=Role.AGENT,
            parts=parts
        )
        
        task_manager.update_task_status(task_id, TaskState.COMPLETED, response_message)
        print(f"A2A task {task_id} completed successfully")

    except Exception as e:
        error_msg = f"Internal error during generation: {str(e)}"
        response_message = Message(
            role=Role.AGENT,
            parts=[Part(text=error_msg)]
        )
        task_manager.update_task_status(task_id, TaskState.FAILED, response_message)
        print(f"A2A task {task_id} exception: {e}")

    finally:
        # Reset the context variable
        task_id_var.reset(token)

@router.post("/v1/message:send")
async def a2a_send_message(request: SendMessageRequest, background_tasks: BackgroundTasks) -> Dict[str, Task]:
    """Handle incoming A2A messages and start a background task.

    Args:
        request (SendMessageRequest): The incoming message request.
        background_tasks (BackgroundTasks): FastAPI background tasks handler.

    Returns:
        Dict[str, Task]: A dictionary containing the created task.

    Raises:
        HTTPException: If the message content is empty.
    """
    # Extract prompt from the first text part
    prompt = ""
    for part in request.message.parts:
        if part.text:
            prompt += part.text + "\n"
    
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="No text content found in message")

    # Create Task
    task = task_manager.create_task(context_id=request.message.context_id)
    
    # Start background processing
    background_tasks.add_task(process_a2a_task, task.id, prompt.strip(), request.message.context_id)
    
    return {"task": task}

@router.get("/v1/tasks/{id}")
async def a2a_get_task(id: str) -> Dict[str, Task]:
    """Retrieve the status of a specific task.

    Args:
        id (str): The task identifier.

    Returns:
        Dict[str, Task]: A dictionary containing the task details.

    Raises:
        HTTPException: If the task is not found.
    """
    task = task_manager.get_task(id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}

@router.get("/v1/extendedAgentCard")
async def a2a_get_agent_card(request: Request) -> AgentCard:
    """Provide the extended agent card describing capabilities.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        AgentCard: The agent card object.
    """
    base_url = str(request.base_url).rstrip("/")
    return AgentCard(
        identity={
            "name": "FormaAI 3D Agent",
            "description": "Generates 3D models (STL/STEP) from natural language descriptions using build123d and Gemini 3 Pro.",
            "author": "FormaAI Team",
            "license": "MIT"
        },
        capabilities={
            "input_types": ["text/plain"],
            "output_types": ["model/stl", "model/step", "text/x-python"],
            "models": ["gemini-3-pro-preview"]
        },
        supported_interfaces=[
            {
                "transport": "http",
                "url": f"{base_url}/v1/message:send"
            }
        ]
    )

@router.get("/.well-known/agent-card.json")
async def a2a_well_known_card(request: Request) -> AgentCard:
    """Serve the well-known agent card for discovery.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        AgentCard: The agent card object.
    """
    return await a2a_get_agent_card(request)
