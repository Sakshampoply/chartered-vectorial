from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from enum import Enum
from app.database import Base


class AssetClass(str, Enum):
    EQUITY = "Equity"
    FIXED_INCOME = "Fixed Income"
    CASH = "Cash"
    ALTERNATIVES = "Alternatives"


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    # REMOVED: age, portfolio_value, risk_tolerance, income_needs, tax_considerations
    # These are now collected in the analysis workflow via AnalysisResult table
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="client", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="client", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="client", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="client", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="client", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    total_value = Column(Float, nullable=False)
    rebalancing_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)  # Purchase price
    current_price = Column(Float, nullable=True)  # Updated from market
    value = Column(Float, nullable=False)  # quantity * price
    asset_class = Column(SQLEnum(AssetClass), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    acquisition_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # csv, txt, pdf
    upload_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="uploaded_files")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    timeline = Column(String(100), nullable=True)
    risk_tolerance = Column(String(50), nullable=True)
    income_requirements = Column(Float, nullable=True)
    liquidity_needs = Column(Text, nullable=True)
    tax_considerations = Column(Text, nullable=True)
    completion_percent = Column(Integer, default=0)  # 0-100
    answers_json = Column(JSON, nullable=True)  # All Q&A responses
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="risk_assessments")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    agent_type = Column(String(100), nullable=False)  # portfolio_analysis, risk_assessment, recommendation
    status = Column(String(50), default="queued")  # queued, running, complete, failed
    progress = Column(Integer, default=0)  # 0-100
    metrics_json = Column(JSON, nullable=True)
    findings_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="agent_runs")


class AnalysisResult(Base):
    """
    Stores complete analysis results from the 3-stage workflow
    
    Workflow Stage 3 produces:
    1. Portfolio Analysis Agent (25% weight) → portfolio_metrics_json
    2. Risk Assessment Agent (25% weight) → risk_metrics_json
    3. Investment Recommendation Agent (50% weight) → recommendation_json
    4. MetricsInterpreterAgent → metrics_summary_json
    5. RecommendationRationaleAgent → rationale_json
    """
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    
    # ====================================================================
    # STAGE 2: RISK & GOALS ASSESSMENT (EXTENDED WITH CASH & TAX INFO)
    # ====================================================================
    risk_profile = Column(String(50), nullable=False)  # conservative, moderate, aggressive
    household_income = Column(Float, nullable=False)  # Annual income USD
    primary_goal = Column(String(100), nullable=True)  # retirement, growth, income, education
    
    # NEW: Cash availability & funding capacity
    cash_on_hand = Column(Float, default=0.0, nullable=False)  # Liquid cash available RIGHT NOW
    monthly_investable_income = Column(Float, default=0.0, nullable=False)  # Recurring monthly from salary
    
    # NEW: Tax situation & timeline
    tax_status = Column(String(50), nullable=True)  # single, married, trust
    investment_horizon_months = Column(Integer, nullable=True)  # When funds needed
    liquidity_needs_pct = Column(Float, default=0.0, nullable=False)  # % of portfolio for emergencies
    
    # NEW: Implementation strategy (derived)
    implementation_scenario = Column(String(50), default="phased_12m", nullable=False)  # immediate, phased_6m, phased_12m, requires_liquidation
    
    # ====================================================================
    # STAGE 3, AGENT 1: PORTFOLIO ANALYSIS (25% weight)
    # ====================================================================
    portfolio_metrics_json = Column(JSON, nullable=True)
    # Structure:
    # {
    #   "allocation": {"AAPL": 0.25, "MSFT": 0.20, ...},
    #   "portfolio_value": 500000.0,
    #   "diversification_score": 0.75,
    #   "concentration_risk": 0.15,
    #   "sector_exposure": {"Technology": 0.40, "Healthcare": 0.30, ...},
    #   "asset_class_exposure": {"Equity": 0.60, "Fixed Income": 0.40}
    # }
    
    # ====================================================================
    # STAGE 3, AGENT 2: RISK ASSESSMENT (25% weight)
    # ====================================================================
    risk_metrics_json = Column(JSON, nullable=True)
    # Structure:
    # {
    #   "sharpe_ratio": 0.85,
    #   "sortino_ratio": 1.2,
    #   "volatility": 0.125,
    #   "beta": 1.05,
    #   "max_drawdown": -0.23,
    #   "var_95": -0.045,
    #   "cvar_95": -0.065,
    #   "risk_level": "moderate"
    # }
    
    # ====================================================================
    # STAGE 3, AGENT 3: INVESTMENT RECOMMENDATION (50% weight)
    # ====================================================================
    recommendation_json = Column(JSON, nullable=True)
    # Structure:
    # {
    #   "recommended_allocation": {"AAPL": 0.20, "MSFT": 0.25, ...},
    #   "projected_return": 0.08,
    #   "projected_volatility": 0.11,
    #   "projected_sharpe": 0.95,
    #   "rebalancing_trades": [
    #     {"action": "buy", "ticker": "AAPL", "quantity": 100, "reason": "underweight"},
    #     {"action": "sell", "ticker": "MSFT", "quantity": 50, "reason": "overweight"}
    #   ],
    #   "implementation_cost": 250.0,
    #   "tax_impact": -500.0,
    #   "execution_plan": "Execute trades over 1-2 weeks"
    # }
    
    # ====================================================================
    # LLM SUMMARIES & EXPLANATIONS
    # ====================================================================
    metrics_summary_json = Column(JSON, nullable=True)
    # Plain English explanation of portfolio metrics
    # {
    #   "allocation_explanation": "Your portfolio is well-diversified...",
    #   "risk_assessment": "Your risk profile matches moderate allocation...",
    #   "key_findings": ["Strong in tech", "Low bond exposure", ...]
    # }
    
    rationale_json = Column(JSON, nullable=True)
    # Explanation of why recommendations make sense
    # {
    #   "recommendation_summary": "We recommend increasing bond allocation...",
    #   "implementation_benefits": "This will improve risk-adjusted returns...",
    #   "key_changes": ["Reduce tech from 40% to 35%", ...]
    # }
    
    # ====================================================================
    # PROGRESS & METADATA
    # ====================================================================
    completed_at = Column(DateTime, nullable=True)  # When analysis finished
    duration_seconds = Column(Float, nullable=True)  # Total execution time
    overall_progress = Column(Float, default=0.0)  # 0.0-1.0 at completion (1.0 = 100%)
    
    # Error tracking
    status = Column(String(50), default="in_progress")  # in_progress, complete, error
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="analysis_results")
    portfolio = relationship("Portfolio")
