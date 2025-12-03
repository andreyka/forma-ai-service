from google.adk.agents import LlmAgent
from google.adk.agents import LlmAgent
from sub_agents.designer.agent import get_designer_agent
from sub_agents.coder.agent import get_coder_agent

# Initialize sub-agents
designer_agent = get_designer_agent()
coder_agent = get_coder_agent()

# Define the Root Agent
root_agent = LlmAgent(
    model="gemini-1.5-pro-002",
    name="FormaRootAgent",
    instruction="""
    You are the root agent for the FormaAI 3D modeling service.
    Your goal is to orchestrate the creation of 3D models.
    
    Workflow:
    1.  Understand the user's request.
    2.  Delegate to the DesignerAgent to create a detailed spec.
    3.  Delegate to the CoderAgent to write and verify the code.
    
    You have tools to call these agents.
    """,
)
