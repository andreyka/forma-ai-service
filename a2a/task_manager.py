from typing import Dict, Optional
import uuid
from datetime import datetime
from .models import Task, TaskStatus, TaskState, Message

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def create_task(self, context_id: Optional[str] = None) -> Task:
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
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, state: TaskState, message: Optional[Message] = None):
        task = self.get_task(task_id)
        if task:
            task.status.state = state
            task.status.timestamp = datetime.utcnow()
            if message:
                task.status.message = message
                task.history.append(message)
