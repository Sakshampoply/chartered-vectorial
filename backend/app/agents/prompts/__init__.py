"""
Prompt templates for all agents
"""

from .chat_intake import *
from .risk_profiling import *
from .document_intelligence import *
from .advisor_copilot import *

__all__ = [
    # Chat intake
    "INTAKE_OPENER",
    "CHAT_INTAKE_SYSTEM_PROMPT",
    
    # Risk profiling
    "RISK_PROFILING_SYSTEM_PROMPT",
    "RISK_QUESTIONS",
    
    # Document intelligence
    "DOCUMENT_PARSING_SYSTEM_PROMPT",
    
    # Advisor copilot
    "ADVISOR_COPILOT_SYSTEM_PROMPT",
]
