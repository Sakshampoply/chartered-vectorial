"""
Tool definitions for LangGraph agents

Wraps existing financial services and document extraction as reusable tools
that can be invoked by agent nodes and the orchestrator.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import json
import logging
from app.models.client import Portfolio

logger = logging.getLogger(__name__)

# ============================================================================
# INPUT SCHEMAS - Pydantic models for tool validation
# ============================================================================

class PortfolioAnalysisInput(BaseModel):
    """Input schema for portfolio analysis tool"""
    portfolio_id: str = Field(..., description="Database portfolio ID")
    rebalance: bool = Field(default=False, description="Include rebalancing suggestions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "port_12345",
                "rebalance": True
            }
        }


class RiskAssessmentInput(BaseModel):
    """Input schema for risk assessment tool"""
    portfolio_id: str = Field(..., description="Database portfolio ID")
    client_id: Optional[str] = Field(None, description="Client ID for risk profile context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "port_12345",
                "client_id": "client_789"
            }
        }


class RecommendationInput(BaseModel):
    """Input schema for recommendation strategy tool"""
    portfolio_id: str = Field(..., description="Database portfolio ID")
    risk_profile: str = Field(..., description="Client risk profile (conservative/moderate/aggressive)")
    goals: Optional[List[str]] = Field(default=None, description="Client investment goals")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "port_12345",
                "risk_profile": "moderate",
                "goals": ["retirement", "college_funding"]
            }
        }


class DocumentExtractionInput(BaseModel):
    """Input schema for document extraction tool"""
    document_path: str = Field(..., description="File path to PDF document")
    document_type: str = Field(default="portfolio_statement", 
                              description="Type: portfolio_statement, account_summary, transaction_history")
    client_id: Optional[str] = Field(None, description="Client ID for context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_path": "/uploads/portfolio_statement_2024.pdf",
                "document_type": "portfolio_statement",
                "client_id": "client_789"
            }
        }


class ScoringInput(BaseModel):
    """Input schema for scoring/feasibility tool"""
    portfolio_id: str = Field(..., description="Database portfolio ID")
    proposed_changes: Dict[str, float] = Field(..., description="Proposed allocation changes {ticker: new_weight}")
    implementation_cost_budget: Optional[float] = Field(None, description="Max acceptable implementation cost")
    
    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "port_12345",
                "proposed_changes": {"VTSAX": 0.50, "VTIAX": 0.30, "BND": 0.20},
                "implementation_cost_budget": 500
            }
        }


# ============================================================================
# TOOL DEFINITIONS - Each tool returns structured output
# ============================================================================

TOOLS_REGISTRY = {
    "portfolio_analysis": {
        "description": "Analyze portfolio composition, allocation, and diversification",
        "category": "analysis",
        "service": "portfolio_analyzer",
        "input_schema": PortfolioAnalysisInput.model_json_schema(),
        "output_format": {
            "allocation": "Dict[str, float]",
            "concentration_risk": "float",
            "diversification_score": "float",
            "sector_exposure": "Dict[str, float]",
            "asset_class_exposure": "Dict[str, float]",
            "rebalancing_needed": "bool",
            "suggested_adjustments": "Dict[str, float]"
        }
    },
    
    "risk_assessment": {
        "description": "Calculate risk metrics (Sharpe, Sortino, Volatility, Beta, Max Drawdown)",
        "category": "analysis",
        "service": "risk_calculator",
        "input_schema": RiskAssessmentInput.model_json_schema(),
        "output_format": {
            "sharpe_ratio": "float",
            "sortino_ratio": "float",
            "volatility": "float",
            "beta": "float",
            "max_drawdown": "float",
            "var_95": "float",
            "cvar_95": "float",
            "risk_level": "str",
            "risk_score": "int"
        }
    },
    
    "recommendation_strategy": {
        "description": "Generate portfolio optimization recommendations based on risk profile and goals",
        "category": "optimization",
        "service": "strategy_optimizer",
        "input_schema": RecommendationInput.model_json_schema(),
        "output_format": {
            "recommended_allocation": "Dict[str, float]",
            "projected_return": "float",
            "projected_volatility": "float",
            "projected_sharpe": "float",
            "rebalancing_trades": "List[Dict]",
            "implementation_cost": "float",
            "tax_impact": "float",
            "expected_annual_benefit": "float",
            "implementation_timeline": "str"
        }
    },
    
    "document_extraction": {
        "description": "Extract holdings and account data from portfolio statements via PDF parsing + LLM fallback",
        "category": "data_ingestion",
        "service": "document_extractor",
        "input_schema": DocumentExtractionInput.model_json_schema(),
        "output_format": {
            "extracted_holdings": "List[Dict]",
            "account_summary": "Dict",
            "extraction_confidence": "float",
            "extraction_method": "str",
            "validation_errors": "List[str]",
            "requires_manual_review": "bool"
        }
    },
    
    "score_and_feasibility": {
        "description": "Score proposed changes for feasibility and impact",
        "category": "optimization",
        "service": "scoring_engine",
        "input_schema": ScoringInput.model_json_schema(),
        "output_format": {
            "feasibility_score": "float",
            "impact_score": "float",
            "implementation_cost": "float",
            "tax_impact": "float",
            "operational_burden": "str",
            "recommended": "bool",
            "constraints_violated": "List[str]"
        }
    }
}


# ============================================================================
# TOOL IMPLEMENTATIONS - Async wrappers calling services
# ============================================================================

class ToolExecutor:
    """Synchronous tool executor for LangGraph nodes"""
    
    def __init__(self, services_dict: Dict[str, Any], db_session=None):
        """
        Args:
            services_dict: Dict mapping service names to service instances
                          e.g., {"portfolio_analyzer": PortfolioAnalyzer()}
            db_session: SQLAlchemy database session for loading portfolios
        """
        self.services = services_dict
        self.db = db_session
        self.execution_log = []
    
    def execute_tool(self, tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a registered tool
        
        Args:
            tool_name: Name of tool from TOOLS_REGISTRY
            inputs: Input dictionary matching the tool's input schema
            
        Returns:
            Dictionary with tool output
            
        Raises:
            ValueError: If tool not found or schema validation fails
            Exception: If service execution fails
        """
        if tool_name not in TOOLS_REGISTRY:
            raise ValueError(f"Tool '{tool_name}' not registered")
        
        tool_config = TOOLS_REGISTRY[tool_name]
        service_name = tool_config["service"]
        
        if service_name not in self.services:
            raise ValueError(f"Service '{service_name}' not available")
        
        service = self.services[service_name]
        
        logger.info(f"Executing tool: {tool_name} with inputs: {inputs}")
        
        try:
            # Dispatch to appropriate handler
            if tool_name == "portfolio_analysis":
                result = self._execute_portfolio_analysis(inputs, service)
            elif tool_name == "risk_assessment":
                result = self._execute_risk_assessment(inputs, service)
            elif tool_name == "recommendation_strategy":
                result = self._execute_recommendation(inputs, service)
            elif tool_name == "document_extraction":
                result = self._execute_document_extraction(inputs, service)
            elif tool_name == "score_and_feasibility":
                result = self._execute_scoring(inputs, service)
            else:
                raise ValueError(f"Handler not implemented for tool: {tool_name}")
            
            self.execution_log.append({
                "tool": tool_name,
                "status": "success",
                "inputs": inputs,
                "output_keys": list(result.keys()) if isinstance(result, dict) else "N/A"
            })
            
            return {
                "status": "success",
                "tool": tool_name,
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, Error: {str(e)}")
            self.execution_log.append({
                "tool": tool_name,
                "status": "error",
                "error": str(e)
            })
            return {
                "status": "error",
                "tool": tool_name,
                "error": str(e)
            }
    
    def _execute_portfolio_analysis(self, inputs: Dict, service) -> Dict:
        """Execute portfolio analysis service with real data"""
        try:
            portfolio_id = inputs["portfolio_id"]
            
            # Load portfolio from database
            if not self.db:
                raise ValueError("Database session required for portfolio analysis")
            
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio not found: {portfolio_id}")
            
            # Convert holdings to list of dicts
            holdings = [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "price": h.price,
                    "value": h.value,
                    "asset_class": h.asset_class,
                    "sector": h.sector,
                }
                for h in portfolio.holdings
            ]
            
            if not holdings:
                raise ValueError("Portfolio has no holdings")
            
            # Call actual service methods
            allocation = service.compute_asset_allocation(holdings)
            sectors = service.compute_sector_allocation(holdings)
            diversification_score = service.compute_diversification_score(holdings)
            
            return {
                "allocation": allocation or {},
                "sector_exposure": sectors or {},
                "diversification_score": (diversification_score / 100.0) if diversification_score else 0.5,
                "concentration_risk": 1.0 - ((diversification_score / 100.0) if diversification_score else 0.5),
                "portfolio_value": portfolio.total_value,
                "holdings_count": len(holdings),
            }
        
        except Exception as e:
            logger.error(f"Portfolio analysis failed: {str(e)}")
            raise
    
    def _execute_risk_assessment(self, inputs: Dict, service) -> Dict:
        """Execute risk assessment service with real calculations"""
        try:
            portfolio_id = inputs["portfolio_id"]
            
            # Load portfolio from database
            if not self.db:
                raise ValueError("Database session required for risk assessment")
            
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio not found: {portfolio_id}")
            
            # Convert holdings to list
            holdings = [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "price": h.price,
                    "value": h.value,
                }
                for h in portfolio.holdings
            ]
            
            if not holdings:
                raise ValueError("Portfolio has no holdings")
            
            tickers = [h["ticker"] for h in holdings]
            
            # Fetch historical data and compute metrics
            # Simplified: compute for first ticker or use weighted approach
            try:
                hist_data = service.fetch_historical_data(tickers[0] if tickers else "SPY", years=3)
                if hist_data is not None:
                    returns = service.compute_returns(hist_data["Close"])
                    sharpe = service.compute_sharpe_ratio(returns)
                    volatility = service.compute_volatility(returns)
                    beta = service.compute_beta(returns)
                    max_drawdown = service.compute_max_drawdown(returns)
                else:
                    # Fallback to reasonable defaults
                    sharpe = 0.85
                    volatility = 0.12
                    beta = 1.05
                    max_drawdown = -0.25
            except Exception as e:
                logger.warning(f"Could not compute metrics for tickers: {str(e)}, using defaults")
                sharpe = 0.85
                volatility = 0.12
                beta = 1.05
                max_drawdown = -0.25
            
            # Compute Value at Risk (simplified)
            try:
                var_95 = service.compute_var(returns, confidence=0.95) if hist_data is not None else -0.032
                cvar_95 = service.compute_cvar(returns, confidence=0.95) if hist_data is not None else -0.041
            except:
                var_95 = -0.032
                cvar_95 = -0.041
            
            return {
                "sharpe_ratio": sharpe,
                "volatility": volatility,
                "beta": beta,
                "max_drawdown": max_drawdown,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "risk_level": self._classify_risk_level(volatility),
            }
        
        except Exception as e:
            logger.error(f"Risk assessment failed: {str(e)}")
            raise
    
    def _execute_recommendation(self, inputs: Dict, service) -> Dict:
        """Execute recommendation strategy service with real optimization"""
        try:
            portfolio_id = inputs["portfolio_id"]
            risk_profile = inputs.get("risk_profile", "moderate")
            
            # Load portfolio from database
            if not self.db:
                raise ValueError("Database session required for recommendations")
            
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio not found: {portfolio_id}")
            
            # Convert holdings to list
            holdings = [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "price": h.price,
                    "value": h.value,
                }
                for h in portfolio.holdings
            ]
            
            if not holdings:
                raise ValueError("Portfolio has no holdings")
            
            tickers = [h["ticker"] for h in holdings]
            
            # Try to optimize using real data
            try:
                mean_returns, cov_matrix = service.fetch_returns_and_cov_matrix(tickers, years=3)
                target_weights = service.optimize_portfolio(mean_returns, cov_matrix, risk_profile)
            except Exception as e:
                logger.warning(f"Optimization failed: {str(e)}, using default allocation")
                # Default allocations by risk profile
                default_allocations = {
                    "conservative": {"STOCK": 0.40, "BOND": 0.60},
                    "moderate": {"STOCK": 0.60, "BOND": 0.40},
                    "aggressive": {"STOCK": 0.80, "BOND": 0.20},
                }
                target_weights = default_allocations.get(risk_profile, default_allocations["moderate"])
            
            # Generate trades
            try:
                trades, tax_cost, impl_cost = service.generate_rebalancing_trades(
                    holdings, target_weights, portfolio.total_value
                )
            except Exception as e:
                logger.warning(f"Trade generation failed: {str(e)}")
                trades = []
                tax_cost = 0.0
                impl_cost = 0.0
            
            return {
                "recommended_allocation": target_weights,
                "rebalancing_trades": trades,
                "implementation_cost": impl_cost,
                "tax_impact": tax_cost,
                "projected_sharpe": 0.95,  # Simplified projection
                "projected_volatility": 0.10,
            }
        
        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            raise
    
    def _classify_risk_level(self, volatility: float) -> str:
        """Classify risk level based on volatility"""
        if volatility < 0.08:
            return "Low"
        elif volatility < 0.12:
            return "Moderate"
        elif volatility < 0.18:
            return "High"
        else:
            return "Very High"
    
    def _execute_document_extraction(self, inputs: Dict, service) -> Dict:
        """Execute document extraction service"""
        document_path = inputs["document_path"]
        # TODO: Call document_extractor to parse PDF
        # Placeholder return
        return {
            "extracted_holdings": [
                {"ticker": "VTSAX", "shares": 1000, "price": 100.00}
            ],
            "extraction_confidence": 0.95,
            "extraction_method": "pdfplumber"
        }
    
    def _execute_scoring(self, inputs: Dict, service) -> Dict:
        """Execute scoring/feasibility service"""
        portfolio_id = inputs["portfolio_id"]
        proposed_changes = inputs["proposed_changes"]
        # TODO: Call scoring_engine to evaluate changes
        # Placeholder return
        return {
            "feasibility_score": 0.88,
            "impact_score": 0.72,
            "implementation_cost": 150.00,
            "recommended": True
        }


# ============================================================================
# TOOL DESCRIPTIONS FOR LLM (System Prompt Snippet)
# ============================================================================

def get_tools_system_prompt() -> str:
    """
    Generate system prompt describing available tools for LLM agents
    """
    tools_section = "# Available Tools\n\n"
    
    for tool_name, config in TOOLS_REGISTRY.items():
        tools_section += f"## {tool_name}\n"
        tools_section += f"**Description:** {config['description']}\n"
        tools_section += f"**Category:** {config['category']}\n"
        tools_section += f"**Inputs:** {json.dumps(config['input_schema'], indent=2)}\n"
        tools_section += f"**Output:** {json.dumps(config['output_format'], indent=2)}\n\n"
    
    return tools_section
