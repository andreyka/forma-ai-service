from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class AgentState:
    user_request: str
    specification: str = ""
    current_code: str = ""
    execution_errors: List[str] = field(default_factory=list)
    artifact_paths: Dict[str, str] = field(default_factory=dict)  # 'stl', 'step', 'screenshots': []
    visual_feedback: List[str] = field(default_factory=list)  # Base64 images or paths
    iteration_count: int = 0
