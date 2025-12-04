"""Task management for the A2A protocol.

This module provides the TaskManager class to create, retrieve,
and update tasks in memory.
"""

from typing import Dict, Optional
import uuid
from datetime import datetime
from .models import Task, TaskStatus, TaskState, Message

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def create_task(self, context_id: Optional[str] = None) -> Task:
        """Create a new task.

        Args:
            context_id (Optional[str]): The context ID. If None, a new one is generated.

        Returns:
            Task: The created task object.
        """
        task_id = str(uuid.uuid4())
        if not context_id:
            context_id = str(uuid.uuid4())
            
        task = Task(
            id=task_id,
            context_id=context_id,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                timestamp=datetime.utcnow()
            )
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by its ID.

        Args:
            task_id (str): The task identifier.

        Returns:
            Optional[Task]: The task object if found, else None.
        """
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, state: TaskState, message: Optional[Message] = None) -> None:
        """Update the status of a task.

        Args:
            task_id (str): The task identifier.
            state (TaskState): The new state of the task.
            message (Optional[Message]): An optional message to append to history.
        """
        task = self.get_task(task_id)
        if task:
            task.status.state = state
            task.status.timestamp = datetime.utcnow()
            if message:
                task.status.message = message
                task.history.append(message)
