"""
Investment Recommendation Agent (Stage 3, Agent 3 - 50% weight)

Responsibilities:
- Generate optimal allocation based on risk profile
- Create specific buy/sell recommendations
- Calculate projected returns and scenarios
- Estimate implementation costs
- Track progress 0→100%
- Generate LLM summary with rationale
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import numpy as np
from app.agents.state import AnalysisState
from app.services.strategy_optimizer import StrategyOptimizer
from app.services.llm_wrapper import LLMWrapper
from app.models.client import Portfolio
from app.database import get_db

logger = logging.getLogger(__name__)


class InvestmentRecommendationAgent:
    """
    Agent 3: Investment Recommendation (50% weight)
    
    Input: portfolio_id + holdings + risk_profile + metrics from Agents 1 & 2
    Output: Target allocation, specific trades, projected returns, scenarios + LLM rationale
    """
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None, db: Optional[Session] = None):
        """
        Initialize agent
        
        Args:
            llm_wrapper: LLMWrapper for LLM-based recommendations
            db: Database session for loading portfolio
        """
        self.llm = llm_wrapper or LLMWrapper(model_name="openai/gpt-oss-120b")
        self.db = db
        self.logger = logger
    
    async def execute(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Execute investment recommendations with progress tracking
        
        Args:
            state: Analysis state with portfolio metrics from Agents 1 & 2
            
        Returns:
            Updated state with recommendations + progress info
        """
        try:
            # Initialize progress
            state["stage_progress"]["recommendation"] = 0.0
            state["stage_status"]["recommendation"] = "running"
            
            portfolio_id = state.get("portfolio_id")
            risk_profile = state.get("risk_profile", "moderate")
            if not portfolio_id:
                raise ValueError("portfolio_id required for recommendations")
            
            # Step 1: Load portfolio (10% progress)
            self.logger.info(f"[Recommendation Agent] Loading portfolio {portfolio_id}")
            state["stage_progress"]["recommendation"] = 0.1
            
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio not found: {portfolio_id}")
            
            holdings = [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "price": h.price,
                    "value": h.value,
                    "asset_class": h.asset_class,
                }
                for h in portfolio.holdings
            ]
            
            tickers = [h["ticker"] for h in holdings]
            
            # Step 2: Fetch returns and covariance (30% progress)
            self.logger.info(f"[Recommendation Agent] Computing optimal allocation")
            state["stage_progress"]["recommendation"] = 0.3
            await asyncio.sleep(0.5)
            
            try:
                mean_returns, cov_matrix = StrategyOptimizer.fetch_returns_and_cov_matrix(
                    tickers, years=3
                )
            except Exception as e:
                self.logger.warning(f"Could not optimize with real data: {str(e)}, using synthetic weights")
                # Fallback to synthetic allocation
                mean_returns = None
                cov_matrix = None
            
            # Step 3: Generate target allocation (55% progress)
            self.logger.info(f"[Recommendation Agent] Generating target allocation")
            state["stage_progress"]["recommendation"] = 0.55
            await asyncio.sleep(0.5)
            
            if mean_returns is not None and cov_matrix is not None:
                try:
                    target_weights = StrategyOptimizer.optimize_portfolio(
                        mean_returns, cov_matrix, risk_profile
                    )
                    state["recommended_allocation"] = target_weights
                except Exception as e:
                    self.logger.warning(f"Optimization failed: {str(e)}, using default allocation")
                    state["recommended_allocation"] = self._get_default_allocation(risk_profile, holdings)
            else:
                state["recommended_allocation"] = self._get_default_allocation(risk_profile, holdings)
            
            # Step 4: Generate trades (75% progress)
            self.logger.info(f"[Recommendation Agent] Generating rebalancing trades")
            state["stage_progress"]["recommendation"] = 0.75
            await asyncio.sleep(0.5)
            
            try:
                trades, tax_cost, impl_cost = StrategyOptimizer.generate_rebalancing_trades(
                    holdings, state["recommended_allocation"], portfolio.total_value
                )
                state["rebalancing_trades"] = trades
                state["tax_impact"] = tax_cost
                state["implementation_cost"] = impl_cost
            except Exception as e:
                self.logger.warning(f"Trade generation failed: {str(e)}")
                state["rebalancing_trades"] = []
                state["tax_impact"] = 0.0
                state["implementation_cost"] = 0.0
            
            # Step 4.5: Validate cash availability and calculate implementation scenario (NEW - Phase 4)
            self.logger.info(f"[Recommendation Agent] Validating cash availability")
            cash_validation = self._validate_cash_and_calculate_scenario(state)
            state["implementation_scenario"] = cash_validation["scenario"]
            state["funding_feasibility"] = cash_validation["feasibility_statement"]
            state["phased_trades_needed"] = cash_validation["phased_trades_needed"]
            
            # Step 5: Calculate projections (90% progress)
            self.logger.info(f"[Recommendation Agent] Calculating projected scenarios")
            state["stage_progress"]["recommendation"] = 0.9
            
            scenarios = self._generate_scenarios(state, risk_profile)
            state["projected_scenarios"] = scenarios
            
            # Extract base case projection
            if "base" in scenarios:
                state["projected_return"] = scenarios["base"].get("return_1yr", 0.07)
                state["projected_volatility"] = scenarios["base"].get("volatility", 0.12)
                state["projected_sharpe"] = scenarios["base"].get("sharpe", 0.85)
            
            # Step 6: Generate LLM recommendation summary (100% progress)
            self.logger.info(f"[Recommendation Agent] Generating recommendation summary")
            state["stage_progress"]["recommendation"] = 1.0
            await asyncio.sleep(0.3)
            
            recommendation_text = await self._generate_recommendation_text(state)
            state["recommendation_text"] = recommendation_text
            
            # Mark complete
            state["stage_status"]["recommendation"] = "complete"
            
            # Update overall progress
            self._update_overall_progress(state)
            
            self.logger.info("[Recommendation Agent] ✓ Complete")
            
            return {
                "status": "complete",
                "metrics": {
                    "target_allocation": state["recommended_allocation"],
                    "recommended_trades": len(state["rebalancing_trades"]),
                    "implementation_cost": state["implementation_cost"],
                    "tax_impact": state["tax_impact"],
                    "projected_sharpe": state["projected_sharpe"],
                    "scenarios": scenarios,
                },
                "recommendation_summary": recommendation_text,
            }
        
        except Exception as e:
            self.logger.error(f"[Recommendation Agent] Error: {str(e)}")
            state["stage_status"]["recommendation"] = "error"
            state["stage_progress"]["recommendation"] = 0.0
            raise
    
    def _get_default_allocation(self, risk_profile: str, holdings: List[Dict]) -> Dict[str, float]:
        """
        Get default allocation based on risk profile, mapping to actual portfolio holdings.
        
        Instead of returning generic "STOCK"/"BOND" labels, maps target asset class allocations
        to actual portfolio holdings by their asset_class attribute.
        
        Conservative: 40% stocks / 60% bonds
        Moderate: 60% stocks / 40% bonds
        Aggressive: 80% stocks / 20% bonds
        """
        # Define target asset class allocation by risk profile
        asset_class_targets = {
            "conservative": {"Equity": 0.40, "Fixed Income": 0.60, "Cash": 0.0, "Alternatives": 0.0},
            "moderate": {"Equity": 0.60, "Fixed Income": 0.35, "Cash": 0.05, "Alternatives": 0.0},
            "aggressive": {"Equity": 0.80, "Fixed Income": 0.10, "Cash": 0.05, "Alternatives": 0.05},
        }
        
        target_allocation = asset_class_targets.get(risk_profile, asset_class_targets["moderate"])
        
        # Map holdings to their asset classes
        holdings_by_class = {}
        for holding in holdings:
            asset_class = str(holding.get("asset_class", "Equity"))
            if asset_class not in holdings_by_class:
                holdings_by_class[asset_class] = []
            holdings_by_class[asset_class].append(holding)
        
        # Distribute target allocations across actual tickers
        ticker_allocation = {}
        
        for asset_class, target_pct in target_allocation.items():
            if target_pct == 0:
                continue
                
            class_holdings = holdings_by_class.get(asset_class, [])
            
            if class_holdings:
                # Distribute the target_pct equally among holdings of this asset class
                pct_per_holding = target_pct / len(class_holdings)
                for holding in class_holdings:
                    ticker = holding["ticker"]
                    ticker_allocation[ticker] = pct_per_holding
        
        # If we have tickers without allocation, ensure they are at least included at some minimal level
        allocated_tickers = set(ticker_allocation.keys())
        all_tickers = set(h["ticker"] for h in holdings)
        unallocated = all_tickers - allocated_tickers
        
        if unallocated and sum(ticker_allocation.values()) < 0.99:
            # Distribute remaining allocation to unallocated tickers
            remaining = 1.0 - sum(ticker_allocation.values())
            pct_per_unallocated = remaining / len(unallocated)
            for ticker in unallocated:
                ticker_allocation[ticker] = pct_per_unallocated
        
        return ticker_allocation
    
    def _generate_scenarios(
        self, state: AnalysisState, risk_profile: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Generate low/base/high return scenarios
        
        Simplified approach based on risk profile
        """
        current_sharpe = state.get("sharpe_ratio") or 0.85
        current_volatility = state.get("volatility") or 0.12
        
        # Ensure values are numeric
        if not isinstance(current_sharpe, (int, float)):
            current_sharpe = 0.85
        if not isinstance(current_volatility, (int, float)):
            current_volatility = 0.12
        
        # Project improvement
        improvement_factor = 1.0 if current_sharpe > 0.8 else 1.15
        
        scenarios = {
            "low": {
                "return_1yr": 0.03,
                "return_5yr": 0.04,
                "volatility": current_volatility * 0.9,
                "sharpe": current_sharpe * 0.8,
                "description": "Recession scenario",
            },
            "base": {
                "return_1yr": 0.07,
                "return_5yr": 0.085,
                "volatility": current_volatility * improvement_factor * 0.95,
                "sharpe": current_sharpe * improvement_factor,
                "description": "Expected scenario",
            },
            "high": {
                "return_1yr": 0.12,
                "return_5yr": 0.14,
                "volatility": current_volatility * improvement_factor * 0.90,
                "sharpe": current_sharpe * improvement_factor * 1.1,
                "description": "Bull market scenario",
            },
        }
        
        return scenarios
    
    def _update_overall_progress(self, state: AnalysisState) -> None:
        """
        Calculate overall weighted progress: (0.25*P) + (0.25*R) + (0.50*Rec)
        """
        p_progress = state["stage_progress"].get("portfolio_analysis", 0.0)
        r_progress = state["stage_progress"].get("risk_assessment", 0.0)
        rec_progress = state["stage_progress"].get("recommendation", 0.0)
        
        overall = (0.25 * p_progress) + (0.25 * r_progress) + (0.50 * rec_progress)
        state["overall_progress"] = overall
    
    def _validate_cash_and_calculate_scenario(self, state: AnalysisState) -> Dict[str, Any]:
        """
        NEW (Phase 4): Validate if cash is available for trades and calculate implementation scenario.
        
        Determines if rebalancing can be done:
        - Immediately (have cash on hand)
        - Phased over months (fund from monthly income)
        - Requires liquidation (no cash or income)
        
        Args:
            state: Analysis state with cash, trades, and monthly income info
            
        Returns:
            {
                "scenario": "immediate" | "phased_6m" | "phased_12m" | "requires_liquidation",
                "feasibility_statement": Plain English explanation,
                "phased_trades_needed": bool
            }
        """
        # Calculate total trade cost
        total_buy_value = sum(t.get("trade_value", 0) for t in state.get("rebalancing_trades", []) if t.get("action") == "buy")
        total_cost = total_buy_value + state.get("tax_impact", 0) + state.get("implementation_cost", 0)
        
        # Get cash availability
        cash_on_hand = state.get("cash_on_hand", 0) or 0
        monthly_income = state.get("monthly_investable_income", 0) or 0
        portfolio_value = state.get("portfolio_value", 1)
        household_income = state.get("household_income", 0) or 0
        
        # Determine scenario
        if cash_on_hand >= total_cost:
            scenario = "immediate"
            feasibility = (
                f"You have ${cash_on_hand:,.0f} in cash and need ${total_cost:,.0f} total. "
                f"Rebalancing can be executed immediately using your available cash."
            )
            phased_needed = False
        
        elif monthly_income > 0:
            months_to_fund = total_cost / monthly_income if monthly_income > 0 else float('inf')
            
            if months_to_fund <= 6:
                scenario = "phased_6m"
                feasibility = (
                    f"You have ${cash_on_hand:,.0f} cash but need ${total_cost:,.0f} total. "
                    f"At ${monthly_income:,.0f}/month from your salary, you can fund this in ~{int(months_to_fund)} months. "
                    f"Recommend phased rebalancing over 6 months."
                )
                phased_needed = True
            
            elif months_to_fund <= 12:
                scenario = "phased_12m"
                feasibility = (
                    f"You have ${cash_on_hand:,.0f} cash but need ${total_cost:,.0f} total. "
                    f"At ${monthly_income:,.0f}/month from your salary, you can fund this in ~{int(months_to_fund)} months. "
                    f"Recommend phased rebalancing over 12 months."
                )
                phased_needed = True
            
            else:
                scenario = "requires_liquidation"
                feasibility = (
                    f"Total rebalancing cost (${total_cost:,.0f}) would take {int(months_to_fund)} months to fund at ${monthly_income:,.0f}/month. "
                    f"Consider liquidating low-conviction positions first to accelerate rebalancing, or implement in phases."
                )
                phased_needed = True
        
        else:
            scenario = "requires_liquidation"
            feasibility = (
                f"You have ${cash_on_hand:,.0f} cash but need ${total_cost:,.0f} total, and no recurring monthly income available. "
                f"You must liquidate existing positions to fund this rebalancing. "
                f"Consider selling positions with losses (tax-loss harvesting) to offset capital gains."
            )
            phased_needed = True
        
        self.logger.info(f"[Recommendation Agent] Cash scenario: {scenario}")
        self.logger.info(f"[Recommendation Agent] Feasibility: {feasibility}")
        
        return {
            "scenario": scenario,
            "feasibility_statement": feasibility,
            "phased_trades_needed": phased_needed,
            "total_cost": total_cost,
            "cash_on_hand": cash_on_hand,
            "monthly_income": monthly_income,
        }
    
    async def _generate_recommendation_text(self, state: AnalysisState) -> str:
        """Generate LLM-powered recommendation explanation"""
        try:
            current_allocation = state.get("allocation", {})
            target_allocation = state.get("recommended_allocation", {})
            trades = state.get("rebalancing_trades", [])
            risk_profile = state.get("risk_profile", "moderate")
            
            trade_summary = ""
            if trades:
                trade_summary = "\n".join([
                    f"  - {t.get('action', '?').upper()} {t.get('ticker', '?')}: {t.get('shares', 0)} shares"
                    for t in trades[:5]
                ])
            
            prompt = f"""
Based on this portfolio analysis and recommendations, provide a 3-4 sentence executive summary:

Current Allocation: {current_allocation}
Target Allocation: {target_allocation}
Risk Profile: {risk_profile}

Recommended Trades:
{trade_summary if trade_summary else 'No significant trades needed'}

Implementation Cost: ${state.get('implementation_cost', 0):.0f}
Projected Improvement: Sharpe ratio {state.get('sharpe_ratio', 0):.2f} → {state.get('projected_sharpe', 0):.2f}

Provide a clear, professional recommendation summary explaining the benefits of rebalancing.
Keep it concise and focus on how it improves the portfolio for the user's {risk_profile} risk profile.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="recommendation",
                temperature=0.6,
            )
            
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error generating recommendation: {str(e)}")
            return "Rebalancing analysis complete. See recommendations and scenarios above for details."
