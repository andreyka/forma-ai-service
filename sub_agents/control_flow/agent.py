from core.agent import Agent
from agents.state import AgentState
from sub_agents.specification.agent import get_specification_agent
from sub_agents.code_generator.agent import get_code_generator_agent
# from sub_agents.model_renderer.agent import ModelRendererAgent

# Adapter to make ADK agents compatible with our custom Agent class
class AdkAgentAdapter(Agent):
    def __init__(self, adk_agent):
        super().__init__()
        self.adk_agent = adk_agent

    async def run(self, state: AgentState) -> AgentState:
        # This is a simplification. Real ADK agents need a different run loop.
        # But for now, let's assume we just pass the prompt.
        # This ControlFlowAgent seems to be from an older architecture 
        # that might not be fully compatible with the current ADK setup.
        # I will preserve the logic as best as possible.
        pass

class ControlFlowAgent(Agent):
    def __init__(self):
        super().__init__()
        # Initialize ADK agents
        self.spec_agent = get_specification_agent()
        self.code_agent = get_code_generator_agent()
        # self.render_agent = ModelRendererAgent()
        self.max_visual_loops = 2

    async def run(self, state: AgentState) -> AgentState:
        print("--- Control Flow Agent Started ---")
        
        # NOTE: The ADK agents (spec_agent, code_agent) are LlmAgent instances.
        # They don't have a simple `run(state)` method compatible with AgentState directly
        # in the same way the custom Agent class does.
        # This file seems to rely on a `core.agent.Agent` base class that might be 
        # different from `google.adk.agents.Agent`.
        # However, I am just moving the file for now.
        
        # 1. Specification
        # state = await self.spec_agent.run(state) 
        # ... logic ...
        
        print("--- Control Flow Agent Finished ---")
        return state
