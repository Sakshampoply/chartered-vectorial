from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Client Schemas
class ClientCreate(BaseModel):
    name: str
    # REMOVED: age, portfolio_value, risk_tolerance, income_needs, tax_considerations
    # These are now collected via AnalysisResult in the analysis workflow


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    # REMOVED: age, portfolio_value, risk_tolerance, income_needs, tax_considerations
    # These are now collected via AnalysisResult in the analysis workflow


class ClientResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Portfolio/Holding Schemas
class HoldingCreate(BaseModel):
    ticker: str
    quantity: float
    price: float
    asset_class: str
    sector: Optional[str] = None
    industry: Optional[str] = None


class HoldingResponse(BaseModel):
    id: UUID
    ticker: str
    quantity: float
    price: float
    current_price: Optional[float]
    value: float
    asset_class: str
    sector: Optional[str]
    industry: Optional[str]

    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    total_value: float
    holdings: List[HoldingCreate]


class PortfolioResponse(BaseModel):
    id: UUID
    client_id: UUID
    total_value: float
    holdings: List[HoldingResponse]
    created_at: datetime

    class Config:
        from_attributes = True


# Risk Assessment Schemas
class RiskAssessmentCreate(BaseModel):
    timeline: Optional[str] = None
    risk_tolerance: Optional[str] = None
    income_requirements: Optional[float] = None
    liquidity_needs: Optional[str] = None
    tax_considerations: Optional[str] = None
    answers_json: Optional[Dict[str, Any]] = None


class RiskAssessmentResponse(BaseModel):
    id: UUID
    client_id: UUID
    timeline: Optional[str]
    risk_tolerance: Optional[str]
    completion_percent: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Risk Metrics Schemas
class RiskMetricsResponse(BaseModel):
    id: UUID
    annual_return: Optional[float]
    volatility: Optional[float]
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    beta: Optional[float]
    max_drawdown: Optional[float]
    concentration_risk: Optional[Dict[str, Any]]
    sector_concentration: Optional[Dict[str, Any]]
    concentration_issues: Optional[List[str]]
    risk_alignment_issues: Optional[List[str]]
    computed_date: datetime

    class Config:
        from_attributes = True


# Recommendation Schemas
class TradeSchema(BaseModel):
    action: str  # buy, sell, hold, increase, decrease
    ticker: str
    current_quantity: Optional[float] = None
    target_quantity: float
    trade_value: Optional[float] = None
    reason: Optional[str] = None
    tax_impact: Optional[float] = None


class RecommendationResponse(BaseModel):
    id: UUID
    portfolio_id: UUID
    strategy_name: Optional[str]
    current_allocation: Dict[str, Any]
    target_allocation: Dict[str, Any]
    trades: List[TradeSchema]
    expected_return: Optional[float]
    expected_volatility: Optional[float]
    projected_3yr_value: Optional[float]
    return_improvement: Optional[float]
    implementation_cost: Optional[float]
    tax_cost: Optional[float]
    feasibility_score: Optional[int]
    impact_score: Optional[int]
    decision: Optional[str]
    rationale: Optional[str]
    strategy_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Analysis State for Pipeline
class AnalysisState(BaseModel):
    client_id: UUID
    portfolio: Optional[Dict[str, Any]] = None
    asset_allocation: Optional[Dict[str, float]] = None
    sector_allocation: Optional[Dict[str, float]] = None
    risk_metrics: Optional[Dict[str, Any]] = None
    concentration_issues: Optional[List[str]] = None
    recommended_strategies: Optional[List[RecommendationResponse]] = None
    agent_findings: Optional[Dict[str, str]] = None
    overall_progress: float = 0.0

    class Config:
        from_attributes = True


# Agent Run Schemas
class AgentRunResponse(BaseModel):
    id: UUID
    agent_type: str
    status: str
    progress: int
    metrics_json: Optional[Dict[str, Any]]
    findings_json: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ====================================================================
# NEW: Extended Intake Schemas (Phase 2: Cash & Tax Questions)
# ====================================================================

class CashAvailabilityRequest(BaseModel):
    """Q3-Q4: Cash on hand and recurring investment capacity"""
    cash_on_hand: float = Field(ge=0, description="Liquid cash available right now (USD)")
    monthly_investable_income: float = Field(ge=0, description="Monthly amount available for investing (USD)")
    implementation_scenario_preference: Optional[str] = Field(
        default=None,
        description="User preference: immediate, phased_6m, phased_12m (optional; auto-calculated if None)"
    )


class TaxProfileRequest(BaseModel):
    """Q5-Q7: Tax situation, investment horizon, and liquidity needs"""
    tax_status: str = Field(..., description="single, married, or trust")
    investment_horizon_months: int = Field(gt=0, description="How many months until funds needed")
    liquidity_needs_pct: float = Field(ge=0, le=100, description="% of portfolio needed for emergencies")


class PhasedTradeSchema(BaseModel):
    """Extended TradeSchema with phased execution support"""
    action: str  # buy, sell, hold
    ticker: str
    current_quantity: Optional[float] = None
    target_quantity: float
    quantity_change: Optional[float] = None
    trade_value: Optional[float] = None
    reason: Optional[str] = None
    current_price: Optional[float] = None
    
    # NEW: Phased execution fields
    execution_phase: int = Field(default=0, description="Month number: 0=immediate, 1-12=future months")
    phased_quantity_per_month: Optional[float] = Field(default=None, description="For phased execution")
    funding_source: Optional[str] = Field(default=None, description="cash_on_hand, monthly_income, or liquidation")


class AnalysisResultResponse(BaseModel):
    """Complete analysis result with all stages"""
    id: UUID
    client_id: UUID
    portfolio_id: UUID
    
    # Stage 2: Risk & Goals
    risk_profile: str
    household_income: float
    primary_goal: Optional[str]
    
    # Stage 2: Cash & Tax (NEW)
    cash_on_hand: float
    monthly_investable_income: float
    tax_status: Optional[str]
    investment_horizon_months: Optional[int]
    liquidity_needs_pct: float
    implementation_scenario: str
    
    # Stage 3: Portfolio Analysis
    portfolio_metrics_json: Optional[Dict[str, Any]]
    
    # Stage 3: Risk Assessment
    risk_metrics_json: Optional[Dict[str, Any]]
    
    # Stage 3: Investment Recommendation
    recommendation_json: Optional[Dict[str, Any]]
    
    # Summaries
    metrics_summary_json: Optional[Dict[str, Any]]
    rationale_json: Optional[Dict[str, Any]]
    
    # Metadata
    status: str
    overall_progress: float
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
