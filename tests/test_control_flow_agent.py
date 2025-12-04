import unittest
from unittest.mock import MagicMock, patch, AsyncMock, create_autospec
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Event
from google.genai.types import Content, Part, FunctionResponse
from sub_agents.control_flow.agent import ControlFlowAgent

# Define a subclass of Event that includes 'content' for autospec
class EventWithContent(Event):
    content: Content | None = None

class TestControlFlowAgent(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session_service = MagicMock(spec=InMemorySessionService)
        self.memory_service = MagicMock(spec=InMemoryMemoryService)
        self.agent = ControlFlowAgent(self.session_service, self.memory_service)

    @patch('sub_agents.control_flow.agent.get_designer_agent', autospec=True)
    @patch('sub_agents.control_flow.agent.get_coder_agent', autospec=True)
    def test_init(self, mock_get_coder, mock_get_designer):
        """Test initialization of ControlFlowAgent."""
        agent = ControlFlowAgent(self.session_service, self.memory_service)
        self.assertEqual(agent.app_name, "forma-ai-service")
        self.assertEqual(agent.session_service, self.session_service)
        self.assertEqual(agent.memory_service, self.memory_service)
        mock_get_designer.assert_called()
        mock_get_coder.assert_called()

    async def test_ensure_session_exists(self):
        """Test _ensure_session when session already exists."""
        self.session_service.get_session.return_value = MagicMock()
        await self.agent._ensure_session("session_1", "user_1")
        self.session_service.get_session.assert_called_with(
            app_name="forma-ai-service", user_id="user_1", session_id="session_1"
        )
        self.session_service.create_session.assert_not_called()

    async def test_ensure_session_creates_new(self):
        """Test _ensure_session when session does not exist."""
        self.session_service.get_session.return_value = None
        await self.agent._ensure_session("session_1", "user_1")
        self.session_service.create_session.assert_called_with(
            app_name="forma-ai-service", user_id="user_1", session_id="session_1"
        )

    def test_extract_or_generate_stl_success(self):
        """Test extraction of STL path from output."""
        output = "Here is the file: outputs/test.stl"
        stl_path, error = self.agent._extract_or_generate_stl(output)
        self.assertEqual(stl_path, "outputs/test.stl")
        self.assertIsNone(error)

    @patch('sub_agents.control_flow.agent.create_cad_model', autospec=True)
    def test_extract_or_generate_stl_fallback_success(self, mock_create_cad):
        """Test fallback generation when no STL path is found but code block exists."""
        output = "```python\nprint('hello')\n```"
        mock_create_cad.return_value = {"success": True, "files": {"stl": "outputs/fallback.stl"}}
        
        stl_path, error = self.agent._extract_or_generate_stl(output)
        
        self.assertEqual(stl_path, "outputs/fallback.stl")
        self.assertIsNone(error)
        mock_create_cad.assert_called_with("print('hello')")

    @patch('sub_agents.control_flow.agent.create_cad_model', autospec=True)
    def test_extract_or_generate_stl_fallback_failure(self, mock_create_cad):
        """Test fallback generation failure."""
        output = "```python\nprint('hello')\n```"
        mock_create_cad.return_value = {"success": False, "error": "Syntax Error"}
        
        stl_path, error = self.agent._extract_or_generate_stl(output)
        
        self.assertIsNone(stl_path)
        self.assertEqual(error, "Syntax Error")

    def test_extract_or_generate_stl_no_code(self):
        """Test failure when neither STL path nor code block is found."""
        output = "Just some text."
        stl_path, error = self.agent._extract_or_generate_stl(output)
        self.assertIsNone(stl_path)
        self.assertEqual(error, "No code block or STL file found.")

    async def test_execute_loop_iteration_retry_on_failure(self):
        """Test retry logic when code generation fails."""
        # Mock _run_coder_step to yield some output
        async def mock_run_coder_step_impl(spec, user_id, session_id, result_container):
            yield "Generating code..."
            result_container["output"] = "Some code output"

        # Use patch.object with autospec=True
        with patch.object(self.agent, '_run_coder_step', autospec=True) as mock_run_coder, \
             patch.object(self.agent, '_extract_or_generate_stl', autospec=True) as mock_extract:
            
            mock_run_coder.side_effect = mock_run_coder_step_impl
            mock_extract.return_value = (None, "Compilation Error")
            
            # Run the iteration
            iterator = self.agent._execute_loop_iteration("spec", "orig_spec", "user", "session")
            
            results = []
            async for item in iterator:
                results.append(item)
            
            # Verify results
            self.assertIn("Generating code...", results)
            
            # The last item should be the tuple (False, next_spec)
            last_item = results[-1]
            self.assertIsInstance(last_item, tuple)
            self.assertFalse(last_item[0])
            self.assertIn("Compilation Error", last_item[1])
            self.assertIn("Original Specification", last_item[1])

    async def test_run_max_loops_on_failure(self):
        """Test that run executes the maximum number of loops on failure."""
        with patch.object(self.agent, '_ensure_session', autospec=True) as mock_ensure, \
             patch.object(self.agent, '_run_designer_step', autospec=True) as mock_designer, \
             patch.object(self.agent, '_execute_loop_iteration', autospec=True) as mock_loop:
            
            mock_designer.return_value = "Initial Spec"
            
            # Mock loop iteration to always fail
            # It yields chunks, then returns (False, next_spec)
            async def mock_loop_impl(current_spec, original_spec, user_id, session_id):
                yield "Loop output"
                yield (False, "New Spec")
            
            mock_loop.side_effect = mock_loop_impl
            
            # Run the agent
            iterator = self.agent.run("prompt", "session_1", "user_1")
            results = []
            async for item in iterator:
                results.append(item)
                
            # Verify calls
            self.assertEqual(mock_loop.call_count, 3)
            self.assertIn("I'm sorry, I was unable to generate the model correctly after multiple attempts.\n", results)

    async def test_verify_model_approved(self):
        """Test _verify_model when designer approves."""
        with patch('sub_agents.control_flow.agent.render_stl', autospec=True) as mock_render, \
             patch.object(self.agent, '_get_designer_feedback', autospec=True) as mock_feedback:
            
            mock_render.return_value = "path/to/image.png"
            mock_feedback.return_value = "APPROVED: Great job!"
            
            is_approved, feedback, png_path = await self.agent._verify_model("model.stl", "spec", "user", "session")
            
            self.assertTrue(is_approved)
            self.assertEqual(feedback, "APPROVED: Great job!")
            self.assertEqual(png_path, "path/to/image.png")

    async def test_verify_model_rejected(self):
        """Test _verify_model when designer rejects."""
        with patch('sub_agents.control_flow.agent.render_stl', autospec=True) as mock_render, \
             patch.object(self.agent, '_get_designer_feedback', autospec=True) as mock_feedback:
            
            mock_render.return_value = "path/to/image.png"
            mock_feedback.return_value = "The model is too small."
            
            is_approved, feedback, png_path = await self.agent._verify_model("model.stl", "spec", "user", "session")
            
            self.assertFalse(is_approved)
            self.assertEqual(feedback, "The model is too small.")

    async def test_execute_loop_iteration_rejection_retry(self):
        """Test loop iteration when model is rejected by designer."""
        with patch.object(self.agent, '_run_coder_step', autospec=True) as mock_run_coder, \
             patch.object(self.agent, '_extract_or_generate_stl', autospec=True) as mock_extract, \
             patch.object(self.agent, '_verify_model', autospec=True) as mock_verify:
            
            # Mock coder output
            async def mock_run_coder_impl(spec, user_id, session_id, result_container):
                yield "Generating..."
                result_container["output"] = "Code"
            mock_run_coder.side_effect = mock_run_coder_impl
            
            # Mock STL extraction success
            mock_extract.return_value = ("model.stl", None)
            
            # Mock verification rejection
            mock_verify.return_value = (False, "Too small", "image.png")
            
            iterator = self.agent._execute_loop_iteration("spec", "orig_spec", "user", "session")
            results = []
            async for item in iterator:
                results.append(item)
            
            # Should have image output
            self.assertIn("Generated Image: image.png\n", results)
            
            # Should have feedback output
            self.assertIn("Designer Feedback: Too small\n", results)
            
            # Last item should be (False, next_spec)
            last_item = results[-1]
            self.assertIsInstance(last_item, tuple)
            self.assertFalse(last_item[0])
            self.assertIn("Too small", last_item[1])

    async def test_run_success(self):
        """Test successful run."""
        with patch.object(self.agent, '_ensure_session', autospec=True), \
             patch.object(self.agent, '_run_designer_step', autospec=True) as mock_designer, \
             patch.object(self.agent, '_execute_loop_iteration', autospec=True) as mock_loop:
            
            mock_designer.return_value = "Spec"
            
            # Mock loop to succeed on first try
            async def mock_loop_impl(current_spec, original_spec, user_id, session_id):
                yield "Success!"
                yield (True, "")
            mock_loop.side_effect = mock_loop_impl
            
            iterator = self.agent.run("prompt", "session")
            results = []
            async for item in iterator:
                results.append(item)
            
            self.assertIn("Success!", results)
            # Should only run once
            self.assertEqual(mock_loop.call_count, 1)

    async def test_run_coder_step_tool_output(self):
        """Test that tool output is included in coder output."""
        # We need to mock the Runner and its run_async method
        with patch('sub_agents.control_flow.agent.Runner', autospec=True) as MockRunner:
            mock_runner_instance = MockRunner.return_value
            
            # Create mock events using the subclass
            mock_event_tool = create_autospec(EventWithContent, instance=True)
            mock_event_tool.content = MagicMock()
            mock_event_tool.content.parts = [
                MagicMock(function_response=MagicMock(response="Tool Result"))
            ]
            mock_event_tool.is_final_response.return_value = False
            
            mock_event_final = create_autospec(EventWithContent, instance=True)
            mock_event_final.content = MagicMock()
            mock_event_final.content.parts = [Part(text="Final Code")]
            mock_event_final.is_final_response.return_value = True
            
            # Mock run_async to yield these events
            async def mock_run_async(*args, **kwargs):
                yield mock_event_tool
                yield mock_event_final
            
            mock_runner_instance.run_async.side_effect = mock_run_async
            
            result_container = {}
            iterator = self.agent._run_coder_step("spec", "user", "session", result_container)
            
            output_chunks = []
            async for chunk in iterator:
                output_chunks.append(chunk)
                
            self.assertEqual(result_container["output"], "\nTool Output: Tool Result\nFinal Code")
            self.assertIn("Final Code", output_chunks)

if __name__ == '__main__':
    unittest.main()
