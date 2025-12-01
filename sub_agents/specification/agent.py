from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from tools.search_tools import SearchTools
from tools.rag_tool import RAGTool
from .prompt import SYSTEM_PROMPT
import os

def get_specification_agent(model_name: str = "gemini-1.5-pro-002") -> LlmAgent:
    search_tool = SearchTools()
    rag_tool = RAGTool()
    
    # Wrap tools for ADK
    def web_search(query: str) -> str:
        """Search the web for information about dimensions, standard sizes, or object details."""
        return search_tool.web_search(query)

    def doc_query(query: str) -> str:
        """Search the build123d documentation for code examples, syntax, and API usage."""
        return rag_tool.query(query)

    # Configure Model
    # Check for vLLM config
    vllm_base = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
    vllm_model = os.getenv("VLLM_MODEL_NAME", "ChatGPT-OSS-120b")
    
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
                frequency_penalty=0.5,
                temperature=0.1
            )
        else:
            print(f"DEBUG: vLLM returned status {response.status_code}. Falling back to Gemini.")
    except Exception as e:
        print(f"DEBUG: vLLM connection failed: {e}. Falling back to Gemini.")

    if not model_client:
        print(f"DEBUG: Using fallback model: {model_name}")
        google_key = os.getenv("GOOGLE_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        print(f"DEBUG: GOOGLE_API_KEY present: {bool(google_key)}")
        print(f"DEBUG: GEMINI_API_KEY present: {bool(gemini_key)}")
        
        # Fallback to Gemini (default LlmAgent behavior if model is string)
        model_client = model_name

    async def fetch_page(url: str) -> str:
        """Fetch the full content of a specific URL found via web_search."""
        return await search_tool.fetch_page(url)

    return LlmAgent(
        model=model_client,
        name="SpecificationAgent",
        instruction=SYSTEM_PROMPT,
        tools=[web_search, doc_query, fetch_page]
    )
