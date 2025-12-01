from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from tools.rag_tool import RAGTool
from tools.cad_tools import create_cad_model
from .prompt import SYSTEM_PROMPT
import os

def get_code_generator_agent(model_name: str = "Qwen/Qwen3-VL-30B-A3B-Instruct-FP8") -> LlmAgent:
    rag_tool = RAGTool()

    # Wrap tools for ADK
    def doc_query(query: str) -> str:
        """Search build123d documentation."""
        return rag_tool.query(query)

    def generate_cad(code: str) -> str:
        """Generates a CAD model from the provided python code."""
        result = create_cad_model(code)
        if result["success"]:
            return f"Success. Files: {result['files']}"
        else:
            return f"Error: {result['error']}"
    
    # Configure Model
    # Check for vLLM config
    vllm_base = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
    vllm_model = os.getenv("VLLM_MODEL_NAME", "Qwen/Qwen3-VL-30B-A3B-Instruct-FP8")
    
    model_client = None
    
    # Use LiteLlm for vLLM support
    import litellm
    litellm._turn_on_debug()

    print(f"DEBUG: VLLM_API_BASE={vllm_base}")
    try:
        import requests
        print(f"DEBUG: Testing connection to {vllm_base}/models...")
        response = requests.get(f"{vllm_base}/models", timeout=2)
        if response.status_code == 200:
            print("DEBUG: vLLM connection successful. Using vLLM.")
            model_client = LiteLlm(
                model=f"openai/{vllm_model}", 
                api_base=vllm_base,
                api_key=os.getenv("VLLM_API_KEY", "EMPTY"),
                max_tokens=4096,
                temperature=0.1
            )
    except Exception:
        pass # Fallback silently or log if needed

    if not model_client:
        # Fallback to Gemini
        model_client = model_name

    return LlmAgent(
        model=model_client,
        name="CodeGeneratorAgent",
        instruction=SYSTEM_PROMPT,
        tools=[doc_query, generate_cad]
    )
