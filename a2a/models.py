"""Data models for the Agent-to-Agent (A2A) protocol.

This module defines Pydantic models for tasks, messages, parts,
and agent capabilities used in the A2A communication.
"""

from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

def to_camel(string: str) -> str:
    return "".join(word.capitalize() if i > 0 else word for i, word in enumerate(string.split("_")))

class A2ABaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        use_enum_values=True
    )

# Enums
class TaskState(str, Enum):
    UNSPECIFIED = "TASK_STATE_UNSPECIFIED"
    SUBMITTED = "TASK_STATE_SUBMITTED"
    WORKING = "TASK_STATE_WORKING"
    COMPLETED = "TASK_STATE_COMPLETED"
    FAILED = "TASK_STATE_FAILED"
    CANCELLED = "TASK_STATE_CANCELLED"
    INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"
    REJECTED = "TASK_STATE_REJECTED"
    AUTH_REQUIRED = "TASK_STATE_AUTH_REQUIRED"

class Role(str, Enum):
    UNSPECIFIED = "ROLE_UNSPECIFIED"
    USER = "ROLE_USER"
    AGENT = "ROLE_AGENT"

# Parts
class FilePart(A2ABaseModel):
    file_with_uri: Optional[str] = None
    file_with_bytes: Optional[bytes] = None
    media_type: Optional[str] = None
    name: Optional[str] = None

class DataPart(A2ABaseModel):
    # Simplified for now, can be expanded
    pass

class Part(A2ABaseModel):
    text: Optional[str] = None
    file: Optional[FilePart] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

# Message
class Message(A2ABaseModel):
    """Represents a message in the A2A protocol.

    Attributes:
        message_id (Optional[str]): Unique identifier for the message.
        context_id (Optional[str]): Context or session ID.
        task_id (Optional[str]): ID of the task this message belongs to.
        role (Role): The role of the message sender (USER or AGENT).
        parts (List[Part]): The content parts of the message.
        metadata (Optional[Dict[str, Any]]): Additional metadata.
        extensions (Optional[str]): Protocol extensions.
        reference_task_ids (Optional[str]): Related task IDs.
    """
    message_id: Optional[str] = None
    context_id: Optional[str] = None
    task_id: Optional[str] = None
    role: Role = Role.USER
    parts: List[Part] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    extensions: Optional[str] = None
    reference_task_ids: Optional[str] = None

# Task
class TaskStatus(A2ABaseModel):
    state: TaskState
    message: Optional[Message] = None
    timestamp: Optional[datetime] = None

class Artifact(A2ABaseModel):
    # Simplified artifact representation
    parts: List[Part] = Field(default_factory=list)

class Task(A2ABaseModel):
    """Represents a task in the A2A system.

    Attributes:
        id (str): Unique task identifier.
        context_id (Optional[str]): Context or session ID.
        status (TaskStatus): Current status of the task.
        artifacts (Optional[Artifact]): Artifacts produced by the task.
        history (List[Message]): Message history associated with the task.
        metadata (Optional[Dict[str, Any]]): Additional metadata.
    """
    id: str
    context_id: Optional[str] = None
    status: TaskStatus
    artifacts: Optional[Artifact] = None
    history: List[Message] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

# Requests
class SendMessageConfiguration(A2ABaseModel):
    accepted_output_modes: Optional[List[str]] = None

class SendMessageRequest(A2ABaseModel):
    message: Message
    configuration: Optional[SendMessageConfiguration] = None

# Agent Card
class AgentCard(A2ABaseModel):
    """Describes the agent's identity and capabilities.

    Attributes:
        type (str): The type of the card (default: "agent-card").
        version (str): The version of the card schema.
        identity (Dict[str, Any]): Identity information (name, description, etc.).
        capabilities (Dict[str, Any]): Capabilities (input/output types, models).
        supported_interfaces (List[Dict[str, str]]): Supported communication interfaces.
    """
    type: str = "agent-card"
    version: str = "1.0"
    identity: Dict[str, Any]
    capabilities: Dict[str, Any]
    supported_interfaces: List[Dict[str, str]]
