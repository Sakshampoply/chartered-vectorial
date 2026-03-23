from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


class RiskMetrics(Base):
    __tablename__ = "risk_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False, unique=True)
    
    # Return metrics
    annual_return = Column(Float, nullable=True)  # %
    expected_return = Column(Float, nullable=True)  # % projected
    
    # Risk metrics
    volatility = Column(Float, nullable=True)  # annualized standard deviation
    sharpe_ratio = Column(Float, nullable=True)  # (return - rf) / volatility
    sortino_ratio = Column(Float, nullable=True)  # downside focused
    beta = Column(Float, nullable=True)  # relative to S&P 500
    max_drawdown = Column(Float, nullable=True)  # worst peak-to-trough
    
    # Correlation & concentration
    correlation_matrix = Column(JSON, nullable=True)  # Dict[str, Dict[str, float]]
    concentration_risk = Column(JSON, nullable=True)  # Holdings >10% of portfolio
    sector_concentration = Column(JSON, nullable=True)  # Sectors >25% of portfolio
    
    # Risk flags
    concentration_issues = Column(JSON, nullable=True)  # List of strings describing issues
    risk_alignment_issues = Column(JSON, nullable=True)  # List of misalignment issues
    
    # Metadata
    computed_date = Column(DateTime, default=datetime.utcnow)
    data_points_count = Column(Integer, nullable=True)  # Number of days of historical data used
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_metrics_id = Column(UUID(as_uuid=True), ForeignKey("risk_metrics.id"), nullable=False)
    
    flag_type = Column(String(100), nullable=False)  # concentration, volatility, liquidity, sector, single_stock
    severity = Column(String(50), nullable=False)  # high, medium, low
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
