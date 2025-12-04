import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from a2a.api import router, _find_generated_files, process_a2a_task
from a2a.models import Task, TaskState, TaskStatus, Message, Role, Part, FilePart

class TestA2AAPI(unittest.TestCase):
    def setUp(self):
        # We need to mount the router to a FastAPI app to use TestClient
        from fastapi import FastAPI
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    @patch('a2a.api.task_manager')
    @patch('a2a.api.BackgroundTasks.add_task')
    def test_send_message_success(self, mock_add_task, mock_task_manager):
        """Test sending a message successfully."""
        mock_task = Task(id="task_1", status=TaskStatus(state=TaskState.SUBMITTED), context_id="ctx_1")
        mock_task_manager.create_task.return_value = mock_task

        response = self.client.post("/v1/message:send", json={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": "Create a cube"}],
                "context_id": "ctx_1"
            }
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task"]["id"], "task_1")
        mock_task_manager.create_task.assert_called()
        mock_add_task.assert_called()

    def test_send_message_empty(self):
        """Test sending an empty message."""
        response = self.client.post("/v1/message:send", json={
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": ""}],
                "context_id": "ctx_1"
            }
        })
        self.assertEqual(response.status_code, 400)

    @patch('a2a.api.task_manager')
    def test_get_task_success(self, mock_task_manager):
        """Test retrieving a task."""
        mock_task = Task(id="task_1", status=TaskStatus(state=TaskState.COMPLETED), context_id="ctx_1")
        mock_task_manager.get_task.return_value = mock_task

        response = self.client.get("/v1/tasks/task_1")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task"]["status"]["state"], "TASK_STATE_COMPLETED")

    @patch('a2a.api.task_manager')
    def test_get_task_not_found(self, mock_task_manager):
        """Test retrieving a non-existent task."""
        mock_task_manager.get_task.return_value = None
        response = self.client.get("/v1/tasks/task_999")
        self.assertEqual(response.status_code, 404)

    @patch('os.path.exists')
    @patch('os.listdir')
    def test_find_generated_files(self, mock_listdir, mock_exists):
        """Test finding generated files."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["task_1.stl", "task_1.step", "other.txt"]
        
        parts = _find_generated_files("task_1", "outputs")
        
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0].file.name, "task_1.stl")
        self.assertEqual(parts[1].file.name, "task_1.step")

    @patch('a2a.api.run_agent')
    @patch('a2a.api.task_manager')
    @patch('a2a.api._find_generated_files')
    @patch('tools.cad_tools.task_id_var')
    async def test_process_a2a_task_success(self, mock_task_id_var, mock_find_files, mock_task_manager, mock_run_agent):
        """Test processing an A2A task."""
        # Mock run_agent as an async generator
        async def mock_agent_gen(*args, **kwargs):
            yield "Response chunk"
        mock_run_agent.return_value = mock_agent_gen()
        
        mock_find_files.return_value = []
        
        await process_a2a_task("task_1", "prompt", "ctx_1")
        
        mock_task_manager.update_task_status.assert_called()
        # Verify completed status
        self.assertEqual(args[0], "task_1")
        self.assertEqual(args[1], TaskState.COMPLETED)

    @patch('a2a.api.run_agent')
    @patch('a2a.api.task_manager')
    @patch('a2a.api._find_generated_files')
    @patch('tools.cad_tools.task_id_var')
    async def test_process_a2a_task_failure(self, mock_task_id_var, mock_find_files, mock_task_manager, mock_run_agent):
        """Test processing an A2A task when agent fails."""
        # Mock run_agent to raise an exception
        async def mock_agent_gen(*args, **kwargs):
            raise Exception("Agent Error")
            yield "Should not be reached" # pragma: no cover
            
        mock_run_agent.return_value = mock_agent_gen()
        
        await process_a2a_task("task_1", "prompt", "ctx_1")
        
        mock_task_manager.update_task_status.assert_called()
        # Verify failed status
        args, _ = mock_task_manager.update_task_status.call_args_list[-1]
        self.assertEqual(args[0], "task_1")
        self.assertEqual(args[1], TaskState.FAILED)
        self.assertIn("Agent Error", args[2]) # Error message should be passed

if __name__ == '__main__':
    unittest.main()
