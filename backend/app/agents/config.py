from dotenv import load_dotenv
load_dotenv(override=True)

"""
Configuration for LLM and agent systems
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration for agent orchestration"""
    
    # OpenRouter API settings
    api_key: str
    api_base: str = "https://openrouter.ai/api/v1"
    
    # Model selection
    model_name: str = "openai/gpt-oss-120b"  # Free, reliable OSS model
    backup_model: str = "mistral-7b-instruct"  # Backup if primary fails
    
    # Generation parameters
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2000
    
    # Timeout and retry settings
    timeout: int = 120
    max_retries: int = 5
    
    # Agent-specific settings
    document_parsing_temperature: float = 0.3  # Low temp for consistent parsing
    chat_intake_temperature: float = 0.7
    risk_profiling_temperature: float = 0.5  # Moderate for questions
    copilot_temperature: float = 0.7  # Conversational for explanations
    
    # Feature flags
    use_streaming: bool = True
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment")
        
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("temperature must be between 0 and 2")
    
    def get_model_for_use_case(self, use_case: str) -> str:
        """Get appropriate model based on use case"""
        # Document parsing and risk profiling need more structured output
        if use_case in ["document_parsing", "risk_profiling"]:
            return self.model_name  # Use primary model
        elif use_case in ["chat_intake", "copilot"]:
            return self.model_name  # Use primary for generation
        else:
            return self.model_name
    
    def get_temperature_for_use_case(self, use_case: str) -> float:
        """Get appropriate temperature based on use case"""
        temps = {
            "document_parsing": self.document_parsing_temperature,
            "chat_intake": self.chat_intake_temperature,
            "risk_profiling": self.risk_profiling_temperature,
            "copilot": self.copilot_temperature,
        }
        return temps.get(use_case, self.temperature)


def get_llm_config() -> LLMConfig:
    """
    Load LLM configuration from environment
    
    Environment variables:
    - OPENROUTER_API_KEY (required)
    - LLM_MODEL (optional, default: openai/gpt-oss-120b)
    - LLM_TEMPERATURE (optional, default: 0.7)
    - LLM_MAX_TOKENS (optional, default: 2000)
    - DEBUG_MODE (optional, default: False)
    
    Returns:
        LLMConfig: Configured LLM settings
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found in environment. "
            "Please add it to .env file."
        )
    
    config = LLMConfig(
        api_key=api_key,
        model_name=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
    )
    
    logger.info(f"LLM Config loaded: model={config.model_name}, temp={config.temperature}")
    return config
