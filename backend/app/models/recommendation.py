from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


class RecommendationStrategy(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    strategy_name = Column(String(255), nullable=True)
    
    # Current state
    current_allocation = Column(JSON, nullable=False)  # {asset_class: %, sector: %}
    current_diversification_score = Column(Integer, nullable=True)
    
    # Target state
    target_allocation = Column(JSON, nullable=False)  # {asset_class: %, sector: %}
    trades = Column(JSON, nullable=False)  # List[{action: 'buy'|'sell'|'hold', ticker: str, quantity: float, reason: str}]
    
    # Financial projections
    expected_return = Column(Float, nullable=True)  # % annual
    expected_volatility = Column(Float, nullable=True)  # % annualized
    projected_3yr_value = Column(Float, nullable=True)  # $ value after 3 years
    return_improvement = Column(Float, nullable=True)  # % vs current
    
    # Costs & implications
    implementation_cost = Column(Float, nullable=True)  # $
    tax_cost = Column(Float, nullable=True)  # $ one-time
    tax_efficiency_gain = Column(Float, nullable=True)  # $
    
    # Scoring
    feasibility_score = Column(Integer, nullable=True)  # 0-100
    impact_score = Column(Integer, nullable=True)  # 0-100
    decision = Column(String(50), nullable=True)  # implement, reject, pending
    
    # Rationale
    rationale = Column(Text, nullable=True)  # LLM-generated explanation
    risks_identified = Column(JSON, nullable=True)  # List[{risk: str, mitigation: str}]
    
    # NEW (Phase 5): Implementation scenario support
    implementation_scenario = Column(String(50), nullable=True)  # immediate, phased_6m, phased_12m, requires_liquidation
    phased_execution_plan = Column(JSON, nullable=True)  # Month-by-month breakdown if phased
    liquidation_candidates = Column(JSON, nullable=True)  # If requires_liquidation, which positions to sell first
    funding_feasibility_statement = Column(Text, nullable=True)  # Plain English explanation of cash availability
    
    # Metadata
    strategy_type = Column(String(50), nullable=True)  # conservative, balanced, aggressive, custom
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=False)
    
    action = Column(String(50), nullable=False)  # buy, sell, hold, increase, decrease
    ticker = Column(String(20), nullable=False)
    current_quantity = Column(Float, nullable=True)
    target_quantity = Column(Float, nullable=False)
    trade_value = Column(Float, nullable=True)  # $ amount
    
    reason = Column(Text, nullable=True)
    tax_impact = Column(Float, nullable=True)  # $ impact
    
    # NEW (Phase 5): Phased execution support
    execution_phase = Column(Integer, default=0, nullable=False)  # 0=immediate, 1-12=future months
    phased_quantity_per_month = Column(Float, nullable=True)  # For phased trades
    funding_source = Column(String(50), nullable=True)  # cash_on_hand, monthly_income, or liquidation
    
    created_at = Column(DateTime, default=datetime.utcnow)
