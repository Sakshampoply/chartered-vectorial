"""
Agents module for Chartered Vectorial

Provides LangGraph-based agentic orchestration for investment analysis workflow.
"""

from .config import LLMConfig, get_llm_config
from .state import AnalysisState, AnalysisStage, AnalysisStateFactory
from .tools import (
    ToolExecutor,
    TOOLS_REGISTRY,
    PortfolioAnalysisInput,
    RiskAssessmentInput,
    RecommendationInput,
    DocumentExtractionInput,
    ScoringInput
)
# Lazy import orchestrator to avoid circular dependencies
# Use: from app.agents.orchestrator import AnalysisOrchestrator
from .document_intelligence import DocumentIntelligenceAgent, run_document_intelligence_agent

__all__ = [
    # Configuration
    "LLMConfig",
    "get_llm_config",
    
    # State Management
    "AnalysisState",
    "AnalysisStage",
    "AnalysisStateFactory",
    
    # Tools
    "ToolExecutor",
    "TOOLS_REGISTRY",
    "PortfolioAnalysisInput",
    "RiskAssessmentInput",
    "RecommendationInput",
    "DocumentExtractionInput",
    "ScoringInput",
    
    # Phase 1: Document Intelligence
    "DocumentIntelligenceAgent",
    "run_document_intelligence_agent",
]
