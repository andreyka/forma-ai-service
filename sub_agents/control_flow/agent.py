"""Control Flow Agent module.

This module defines the ControlFlowAgent, which orchestrates the interaction
between the Designer and Coder agents to generate 3D models.
"""

import re
from typing import AsyncGenerator
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai.types import Content, Part

import logging
from sub_agents.designer.agent import get_designer_agent
from sub_agents.coder.agent import get_coder_agent
from sub_agents.designer.agent import get_designer_agent
from sub_agents.coder.agent import get_coder_agent
from tools.renderer import render_stl
from tools.cad_tools import create_cad_model

logger = logging.getLogger(__name__)

class ControlFlowAgent:
    """Orchestrates the multi-agent workflow for 3D model generation.

    Attributes:
        app_name (str): The name of the application.
        session_service: Service for managing user sessions.
        memory_service: Service for managing agent memory.
        designer_agent: The initialized Designer Agent.
        coder_agent: The initialized Coder Agent.
    """

    def __init__(self, session_service: InMemorySessionService, memory_service: InMemoryMemoryService):
        """Initializes the ControlFlowAgent.

        Args:
            session_service (InMemorySessionService): Service for managing user sessions.
            memory_service (InMemoryMemoryService): Service for managing agent memory.
        """
        self.app_name = "forma-ai-service"
        self.session_service = session_service
        self.memory_service = memory_service
        
        # Initialize sub-agents
        self.designer_agent = get_designer_agent()
        self.coder_agent = get_coder_agent()

    async def _ensure_session(self, session_id: str, user_id: str) -> None:
        """Ensures a session exists for the user.

        Args:
            session_id (str): The unique identifier for the session.
            user_id (str): The unique identifier for the user.
        """
        logger.info(f"ControlFlow: Ensuring session {session_id} exists for user {user_id}")
        session = await self.session_service.get_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
        if not session:
            logger.info(f"ControlFlow: Session not found. Creating new session...")
            await self.session_service.create_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
            logger.info("ControlFlow: Session created.")
        else:
            logger.info("ControlFlow: Session found.")

    async def _run_designer_step(self, prompt: str, user_id: str, session_id: str) -> str:
        """Runs the Designer Agent to generate a specification.

        Args:
            prompt (str): The user's initial request.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.

        Returns:
            str: The generated design specification as a string.
        """
        logger.info("--- Running Designer Agent ---")
        designer_runner = Runner(
            agent=self.designer_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        designer_input = Content(parts=[Part(text=prompt)], role="user")
        designer_output = ""
        
        async for event in designer_runner.run_async(user_id=user_id, session_id=session_id, new_message=designer_input):
            if event.is_final_response() and event.content and event.content.parts:
                designer_output = event.content.parts[0].text
                logger.info(f"ControlFlow: Designer Agent Output:\n{designer_output}")
        
        return designer_output

    async def _run_coder_step(self, spec: str, user_id: str, session_id: str, result_container: dict[str, str]) -> AsyncGenerator[str, None]:
        """Runs the Coder Agent to generate code.

        Args:
            spec (str): The design specification.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.
            result_container (dict[str, str]): A dictionary to store the full output string.

        Yields:
            str: Chunks of the generated text output.
        """
        coder_runner = Runner(
            agent=self.coder_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        coder_input = Content(parts=[Part(text=f"Specification:\n{spec}")], role="user")
        coder_output = ""
        
        async for event in coder_runner.run_async(user_id=user_id, session_id=session_id, new_message=coder_input):
            if event.content:
                 tool_output = self._parse_tool_output(event.content)
                 if tool_output:
                     coder_output += f"\nTool Output: {tool_output}"
            
            if event.is_final_response() and event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                if text_parts:
                    chunk = "\n" + "\n".join(text_parts)
                    coder_output += chunk
                    yield "\n".join(text_parts)
        
        result_container["output"] = coder_output
        logger.info(f"ControlFlow: Coder Output Raw: {coder_output}")

    def _parse_tool_output(self, content: Content) -> str | None:
        """Parses tool output from the content."""
        for part in content.parts:
            if part.function_response:
                return part.function_response.response
        return None

    def _extract_or_generate_stl(self, coder_output: str) -> tuple[str | None, str | None]:
        """Extracts STL path from output or attempts fallback generation.

        Args:
            coder_output (str): The full text output from the Coder Agent.

        Returns:
            tuple[str | None, str | None]: A tuple containing (stl_path, error_message).
                If successful, stl_path is str and error_message is None.
                If failed, stl_path is None and error_message is str.
        """
        # Extract STL path
        stl_match = re.search(r"outputs/[\w-]+\.stl", coder_output)
        
        if stl_match:
            return stl_match.group(0), None
            
        if stl_match:
            return stl_match.group(0), None
            
        logger.info("ControlFlow: No STL file found in output. Checking for code block...")
        # Fallback: Check if code was outputted in markdown
        code_match = re.search(r"```python(.*?)```", coder_output, re.DOTALL)
        if code_match:
            logger.info("ControlFlow: Found code block. Executing fallback generation...")
            code = code_match.group(1).strip()
            logger.info("ControlFlow: Found code block. Executing fallback generation...")
            code = code_match.group(1).strip()
            result = create_cad_model(code)
            if result["success"]:
                logger.info(f"ControlFlow: Fallback generation successful. Files: {result['files']}")
                # We need to find the STL in the new result
                # The result['files'] is a dict {'step': ..., 'stl': ...}
                return result['files']['stl'], None
            else:
                logger.error(f"ControlFlow: Fallback generation failed: {result['error']}")
                return None, result['error']
        
        return None, "No code block or STL file found."

    async def _get_designer_feedback(self, png_path: str, original_spec: str, user_id: str, session_id: str) -> str:
        """Requests feedback from the Designer Agent on the rendered image.

        Args:
            png_path (str): Path to the rendered PNG image.
            original_spec (str): The original design specification.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.

        Returns:
            str: The feedback text from the Designer Agent.
        """
        logger.info("--- Requesting Designer Feedback ---")
        designer_runner = Runner(
            agent=self.designer_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        with open(png_path, "rb") as f:
            image_data = f.read()
            
        feedback_prompt = "Here is the rendered image of the generated model. Compare it against the original specification. If it is correct, reply with 'APPROVED' followed by a friendly message to the user describing the model and any nuances (e.g. 'Here is your 3d model...'). If it is incorrect, describe what is wrong so the coder can fix it."
        
        feedback_input = Content(parts=[
            Part(text=feedback_prompt),
            Part(inline_data={"mime_type": "image/png", "data": image_data})
        ], role="user")
        
        feedback_output = ""
        async for event in designer_runner.run_async(user_id=user_id, session_id=session_id, new_message=feedback_input):
            if event.is_final_response() and event.content and event.content.parts:
                feedback_output = event.content.parts[0].text
                logger.info(f"ControlFlow: Designer Feedback:\n{feedback_output}")
        
        return feedback_output


    async def _verify_model(self, stl_path: str, original_spec: str, user_id: str, session_id: str) -> tuple[bool, str, str | None]:
        """Renders the model and gets feedback from the Designer.

        Args:
            stl_path: Path to the STL file.
            original_spec: The original specification.
            user_id: User ID.
            session_id: Session ID.

        Returns:
            tuple: (is_approved, feedback_text, png_path)
        """
        logger.info(f"ControlFlow: Found STL at {stl_path}")
        
        # Render STL
        png_path = render_stl(stl_path)
        if not png_path:
            logger.error("ControlFlow: Failed to render STL.")
            return False, "Failed to render STL.", None
            
        logger.info(f"ControlFlow: Rendered image at {png_path}")
        
        # Ask Designer for Feedback
        feedback_output = await self._get_designer_feedback(png_path, original_spec, user_id, session_id)
        
        is_approved = "APPROVED" in feedback_output
        return is_approved, feedback_output, png_path

    async def _execute_loop_iteration(self, current_spec: str, original_spec: str, user_id: str, session_id: str) -> AsyncGenerator[str | tuple[bool, str], None]:
        """Executes one iteration of the feedback loop.

        Args:
            current_spec (str): The current specification to code.
            original_spec (str): The original specification for reference.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.

        Yields:
            Union[str, tuple[bool, str]]: Chunks of text output, and finally a tuple (is_approved, next_spec).
        """
        # 1. Generate Model
        # Note: We can't easily stream the coder output here if we refactor to _generate_model 
        # unless we pass the yield callback or keep the generator logic inline.
        # To preserve streaming, we'll keep the generator call here but use the helper logic for the rest.
        
        coder_result = {}
        async for chunk in self._run_coder_step(current_spec, user_id, session_id, coder_result):
            yield chunk
            
        coder_output = coder_result.get("output", "")
        stl_path, generation_error = self._extract_or_generate_stl(coder_output)
        
        if not stl_path:
            logger.error(f"ControlFlow: Generation failed. Error: {generation_error}")
            logger.info("ControlFlow: Sending error back to Coder...")
            next_spec = f"Original Specification:\n{original_spec}\n\nPrevious attempt failed with error:\n{generation_error}\n\nPlease fix the code."
            yield (False, next_spec)
            return

        # 2. Verify Model
        is_approved, feedback_output, png_path = await self._verify_model(stl_path, original_spec, user_id, session_id)
        
        if png_path:
            yield f"Generated Image: {png_path}\n"
        else:
            yield "\nFailed to render STL.\n"
            yield (False, current_spec)
            return

        if is_approved:
            logger.info("ControlFlow: Design Approved.")
            friendly_msg = feedback_output.replace("APPROVED", "").strip()
            if not friendly_msg:
                    friendly_msg = "Here is your 3D model."
            yield f"{friendly_msg}\n"
            yield (True, "")
        else:
            logger.info("ControlFlow: Design Rejected. Retrying...")
            yield f"Designer Feedback: {feedback_output}\n"
            next_spec = f"Original Specification:\n{original_spec}\n\nFeedback on previous attempt:\n{feedback_output}\n\nPlease fix the code based on this feedback."
            yield (False, next_spec)

    async def run(self, prompt: str, session_id: str, user_id: str = "user") -> AsyncGenerator[str, None]:
        """Executes the agent workflow: Designer -> Coder -> Renderer -> Designer (Feedback) -> Coder (Fix).

        Args:
            prompt (str): The user's request.
            session_id (str): The unique identifier for the session.
            user_id (str): The unique identifier for the user.

        Yields:
            str: Chunks of text output describing the process and results.
        """
        await self._ensure_session(session_id, user_id)

        # Run Designer Agent first to build the initial task / specification. 
        designer_output = await self._run_designer_step(prompt, user_id, session_id)
        yield f"Design Specification:\n{designer_output[:100]}...\n"

        # After design specification is generated, run the loops of coder -> renderer -> designer -> coder until approved or max loops reached.
        max_loops = 3
        current_spec = designer_output
        
        for loop in range(max_loops):
            logger.info(f"--- Running Coder Agent (Loop {loop+1}) ---")
            
            async for chunk in self._execute_loop_iteration(current_spec, designer_output, user_id, session_id):
                if isinstance(chunk, tuple):
                    # Final result of the iteration
                    is_approved, next_spec = chunk
                    if is_approved:
                        return
                    current_spec = next_spec
                else:
                    # Streaming output
                    yield chunk
        
        # If loop finishes without approval
        yield "I'm sorry, I was unable to generate the model correctly after multiple attempts.\n"
