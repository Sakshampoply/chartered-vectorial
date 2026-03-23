"""
State definition for LangGraph analysis orchestrator

Defines the shared state that flows through all agent nodes in the workflow.
"""

from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AnalysisStage(str, Enum):
    """Enumeration of analysis workflow stages - 5 main stages per assignment"""
    # Stage 1: Client Profile Gathering (File upload)
    DOCUMENT_INGESTION = "document_ingestion"
    
    # Stage 2: Risk & Goals Assessment (2-3 questions)
    INFO_COLLECTION = "info_collection"
    
    # Stage 3: AI-Powered Analysis (3 specialized agents)
    PORTFOLIO_ANALYSIS = "portfolio_analysis_running"
    RISK_ASSESSMENT = "risk_assessment_running"
    RECOMMENDATION = "recommendation_running"
    
    # Terminal states
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"


class AnalysisState(TypedDict):
    """
    Shared state for LangGraph orchestrator
    
    Flows through all nodes sequentially with updates at each stage.
    Each node reads from state, executes work, and returns updates.
    """
    
    # ========================================================================
    # METADATA
    # ========================================================================
    
    analysis_id: str  # Unique identifier for this analysis run
    client_id: str  # Client from database
    portfolio_id: Optional[str]  # Portfolio from database (optional until created)
    created_at: str  # ISO timestamp when analysis started
    stage: AnalysisStage  # Current workflow stage
    
    # ========================================================================
    # CLIENT/PROFILE DATA
    # ========================================================================
    
    client_name: Optional[str]  # Extract from intake chat
    client_age: Optional[int]  # Extract from intake chat
    client_email: Optional[str]  # From user profile
    client_phone: Optional[str]  # From user profile
    
    # Stage 2: Risk & Goals Assessment (2-3 key questions only)
    risk_profile: Optional[str]  # "conservative" | "moderate" | "aggressive" - REQUIRED
    household_income: Optional[float]  # Annual household income USD - REQUIRED
    primary_goal: Optional[str]  # "retirement" | "growth" | "income" | "education" - OPTIONAL
    
    # Stage 2: Cash & Tax Profile (NEW Q3-Q7)
    cash_on_hand: Optional[float]  # Liquid cash available RIGHT NOW - Q3
    monthly_investable_income: Optional[float]  # Monthly amount available for investing - Q4
    tax_status: Optional[str]  # "single" | "married" | "trust" - Q5
    investment_horizon_months: Optional[int]  # Months until funds needed - Q6
    liquidity_needs_pct: Optional[float]  # % of portfolio for emergencies - Q7
    implementation_scenario: Optional[str]  # "immediate" | "phased_6m" | "phased_12m" | "requires_liquidation"
    
    # Info collection tracking
    info_collection_complete: bool = False  # Both required fields filled?
    info_collection_progress: float = 0.0  # 0.0 to 1.0 (for UI: 0%, 50%, 100%)
    
    # Legacy fields (kept for backward compat, may deprecate)
    risk_score: Optional[int]  # 0-100 score
    investment_horizon: Optional[int]  # Years
    max_acceptable_loss: Optional[float]  # Percentage
    liquidity_needs: Optional[float]  # Amount, USD
    investment_goals: List[str]  # e.g., ["retirement", "college_funding"]
    additional_notes: Optional[str]  # Client context
    
    # ========================================================================
    # DOCUMENT EXTRACTION (Stage 1)
    # ========================================================================
    
    uploaded_documents: List[Dict[str, Any]] = field(default_factory=list)  # List of {"path": str, "type": str}
    extraction_results: Optional[Dict[str, Any]]  # Holdings extracted from documents
    extracted_holdings: List[Dict[str, Any]] = field(default_factory=list)  # [{"ticker": str, "shares": float, "price": float}]
    document_extraction_confidence: Optional[float]  # 0.0-1.0
    document_extraction_method: Optional[str]  # "pdfplumber" | "unstructured" | "llm_fallback"
    extraction_errors: List[str] = field(default_factory=list)  # Validation/parsing errors
    requires_manual_review: bool = False  # Flag if extraction uncertain
    
    # ========================================================================
    # CHAT INTAKE (Stage 1)
    # ========================================================================
    
    chat_history: List[Dict[str, str]] = field(default_factory=list)  # [{"role": "user"|"assistant", "content": str}]
    chat_messages_count: int = 0  # Number of turns in intake conversation
    profile_complete: bool = False  # All required fields filled?
    missing_fields: List[str] = field(default_factory=list)  # Fields still needed
    
    # ========================================================================
    # RISK PROFILING (Stage 2)
    # ========================================================================
    
    risk_assessment_history: List[Dict[str, Any]] = field(default_factory=list)  # Progression of answers
    risk_questions_answered: int = 0  # 0-8
    risk_assessment_complete: bool = False  # >= 70% answered?
    risk_assessment_method: Optional[str]  # "questionnaire" | "hybrid_llm"
    
    # ========================================================================
    # STAGE 3: PROGRESS TRACKING FOR 3 AGENTS (AI-Powered Analysis)
    # ========================================================================
    
    # Progress tracking for weighted agents
    stage_progress: Dict[str, float] = field(default_factory=dict)  # {agent_name: 0.0-1.0}
    stage_status: Dict[str, str] = field(default_factory=dict)  # {agent_name: "queued"|"running"|"complete"}
    overall_progress: float = 0.0  # Weighted: (0.25*portfolio) + (0.25*risk) + (0.50*recommendation)
    
    # ========================================================================
    # PORTFOLIO ANALYSIS (Stage 3, Agent 1 - 25% weight)
    # ========================================================================
    
    allocation: Optional[Dict[str, float]]  # Current allocation: {ticker_or_class: weight}
    portfolio_value: Optional[float]  # Total portfolio size in USD
    concentration_risk: Optional[float]  # 0.0-1.0, higher = more concentrated
    diversification_score: Optional[float]  # 0.0-1.0, higher = better diversified
    sector_exposure: Optional[Dict[str, float]]  # Sector breakdown
    asset_class_exposure: Optional[Dict[str, float]]  # Stock/Bond/Cash breakdown
    rebalancing_needed: bool = False  # Does allocation need adjustment?
    
    # ========================================================================
    # RISK ASSESSMENT (Stage 3, Agent 2 - 25% weight)
    # ========================================================================
    
    sharpe_ratio: Optional[float]  # Risk-adjusted return metric
    sortino_ratio: Optional[float]  # Downside risk-adjusted metric
    volatility: Optional[float]  # Annual standard deviation
    beta: Optional[float]  # Market sensitivity
    max_drawdown: Optional[float]  # Worst historical loss
    var_95: Optional[float]  # Value at Risk (95% confidence)
    cvar_95: Optional[float]  # Conditional VaR
    risk_level: Optional[str]  # Computed risk category
    
    # ========================================================================
    # RECOMMENDATION (Stage 3, Agent 3 - 50% weight)
    # ========================================================================
    
    recommended_allocation: Optional[Dict[str, float]]  # Target allocation
    projected_return: Optional[float]  # Expected annual return %
    projected_volatility: Optional[float]  # Expected volatility %
    projected_sharpe: Optional[float]  # Expected Sharpe ratio
    rebalancing_trades: List[Dict[str, Any]] = field(default_factory=list)  # Buy/sell actions
    implementation_cost: Optional[float]  # Total transaction cost
    tax_impact: Optional[float]  # Estimated tax effect
    expected_annual_benefit: Optional[float]  # Benefit if implemented
    implementation_timeline: Optional[str]  # "immediate" | "gradual_6mo" | "dollar_cost_avg"
    
    # ========================================================================
    # SCORING & FEASIBILITY (Agent 3 sub-component - embedded in recommendations)
    # ========================================================================
    
    feasibility_score: Optional[float]  # 0.0-1.0
    impact_score: Optional[float]  # 0.0-1.0
    operational_burden: Optional[str]  # "low" | "medium" | "high"
    constraints_violated: List[str] = field(default_factory=list)  # Any breached constraints
    recommendation_accepted: Optional[bool]  # User approved?
    
    # ========================================================================
    # ADVISOR COPILOT (Post-Analysis: Q&A with stored metrics)
    # ========================================================================
    
    copilot_messages: List[Dict[str, str]] = field(default_factory=list)  # [{"role": "user"|"assistant", "content": str}]
    copilot_context: Optional[Dict[str, Any]]  # Analysis snapshot for Q&A
    what_if_scenarios: List[Dict[str, Any]] = field(default_factory=list)  # Explored scenarios
    
    # ========================================================================
    # EXECUTION & FOLLOW-UP
    # ========================================================================
    
    execution_plan: Optional[str]  # How to implement recommendation
    advisor_next_steps: Optional[str]  # Action items for advisor
    client_next_steps: Optional[str]  # Action items for client
    follow_up_date: Optional[str]  # Recommended follow-up date
    
    # ========================================================================
    # ERROR TRACKING & LOGGING
    # ========================================================================
    
    errors: List[Dict[str, Any]] = field(default_factory=list)  # [{"stage": str, "error": str, "timestamp": str}]
    warnings: List[str] = field(default_factory=list)  # Non-fatal alerts
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)  # Audit trail
    token_count: int = 0  # Cumulative LLM tokens used
    estimated_cost: float = 0.0  # Cumulative API cost estimate
    duration_seconds: Optional[float]  # Total execution time


@dataclass
class AnalysisStateFactory:
    """Factory for creating new analysis states"""
    
    @staticmethod
    def create_new(analysis_id: str, client_id: str) -> AnalysisState:
        """Create a new analysis state with defaults"""
        return AnalysisState(
            analysis_id=analysis_id,
            client_id=client_id,
            portfolio_id=None,
            created_at=datetime.now().isoformat(),
            stage=AnalysisStage.DOCUMENT_INGESTION,
            
            # Client data
            client_name=None,
            client_age=None,
            client_email=None,
            client_phone=None,
            
            # Risk profile - Stage 2
            risk_profile=None,
            household_income=None,
            primary_goal=None,
            info_collection_complete=False,
            info_collection_progress=0.0,
            
            # Cash & Tax Profile - Stage 2 NEW
            cash_on_hand=None,
            monthly_investable_income=None,
            tax_status=None,
            investment_horizon_months=None,
            liquidity_needs_pct=None,
            implementation_scenario=None,
            
            # Legacy fields
            risk_score=None,
            investment_horizon=None,
            max_acceptable_loss=None,
            liquidity_needs=None,
            investment_goals=[],
            additional_notes=None,
            
            # Document extraction
            uploaded_documents=[],
            extraction_results=None,
            extracted_holdings=[],
            document_extraction_confidence=None,
            document_extraction_method=None,
            extraction_errors=[],
            requires_manual_review=False,
            
            # Chat intake
            chat_history=[],
            chat_messages_count=0,
            profile_complete=False,
            missing_fields=[],
            
            # Risk profiling
            risk_assessment_history=[],
            risk_questions_answered=0,
            risk_assessment_complete=False,
            risk_assessment_method=None,
            
            # Progress tracking for Stage 3
            stage_progress={},
            stage_status={},
            overall_progress=0.0,
            
            # Portfolio analysis
            allocation=None,
            portfolio_value=None,
            concentration_risk=None,
            diversification_score=None,
            sector_exposure=None,
            asset_class_exposure=None,
            rebalancing_needed=False,
            
            # Risk metrics
            sharpe_ratio=None,
            sortino_ratio=None,
            volatility=None,
            beta=None,
            max_drawdown=None,
            var_95=None,
            cvar_95=None,
            risk_level=None,
            
            # Recommendation
            recommended_allocation=None,
            projected_return=None,
            projected_volatility=None,
            projected_sharpe=None,
            rebalancing_trades=[],
            implementation_cost=None,
            tax_impact=None,
            expected_annual_benefit=None,
            implementation_timeline=None,
            
            # Scoring
            feasibility_score=None,
            impact_score=None,
            operational_burden=None,
            constraints_violated=[],
            recommendation_accepted=None,
            
            # Copilot
            copilot_messages=[],
            copilot_context=None,
            what_if_scenarios=[],
            
            # Execution
            execution_plan=None,
            advisor_next_steps=None,
            client_next_steps=None,
            follow_up_date=None,
            
            # Error tracking
            errors=[],
            warnings=[],
            execution_steps=[],
            token_count=0,
            estimated_cost=0.0,
            duration_seconds=None,
        )
    
    @staticmethod
    def add_error(state: AnalysisState, stage: str, error: str) -> AnalysisState:
        """Add error to state and log"""
        state["errors"].append({
            "stage": stage,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        state["stage"] = AnalysisStage.ERROR
        return state
    
    @staticmethod
    def add_warning(state: AnalysisState, warning: str) -> AnalysisState:
        """Add non-fatal warning"""
        state["warnings"].append(warning)
        return state
    
    @staticmethod
    def log_step(state: AnalysisState, step_name: str, details: Optional[Dict] = None) -> AnalysisState:
        """Log an execution step for audit trail"""
        state["execution_steps"].append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
        return state
