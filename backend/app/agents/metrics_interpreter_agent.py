"""
Metrics Interpreter Agent (Post-Analysis)

Responsibility:
- Convert computed financial metrics into plain English explanations
- Explain what each metric means for this specific portfolio
- Highlight key findings from all 3 agents
- Make metrics accessible to non-financial users
"""

import logging
from typing import Dict, Any, Optional
from app.agents.state import AnalysisState
from app.services.llm_wrapper import LLMWrapper

logger = logging.getLogger(__name__)


class MetricsInterpreterAgent:
    """
    Post-analysis agent that interprets financial metrics in plain English
    
    Input: All computed metrics from 3 agents
    Output: Natural language explanations and summaries
    """
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None):
        """Initialize agent"""
        self.llm = llm_wrapper or LLMWrapper(model_name="openai/gpt-oss-120b")
        self.logger = logger
    
    async def interpret_all_metrics(self, state: AnalysisState) -> Dict[str, str]:
        """
        Generate interpretations for all major metrics
        
        Args:
            state: Complete analysis state with all metrics
            
        Returns:
            Dictionary of {metric_group: interpretation_text}
        """
        try:
            interpretations = {}
            
            # Portfolio composition interpretation
            interpretations["portfolio_composition"] = await self._interpret_portfolio(state)
            
            # Risk profile interpretation
            interpretations["risk_profile"] = await self._interpret_risk_metrics(state)
            
            # Allocation comparison interpretation
            interpretations["allocation_comparison"] = await self._interpret_allocation_shift(state)
            
            # Opportunities interpretation
            interpretations["opportunities"] = await self._interpret_opportunities(state)
            
            return interpretations
        
        except Exception as e:
            self.logger.error(f"Error interpreting metrics: {str(e)}")
            return {"error": f"Could not interpret metrics: {str(e)}"}
    
    async def _interpret_portfolio(self, state: AnalysisState) -> str:
        """Interpret portfolio composition and diversification"""
        try:
            div_score = state.get('diversification_score') or 0
            portfolio_val = state.get('portfolio_value') or 0
            holdings_count = len(state.get('extracted_holdings', []))
            
            prompt = f"""
Interpret this portfolio composition in plain English (2-3 sentences):

Allocation: {state.get('allocation', {})}
Sector Exposure: {state.get('sector_exposure', {})}
Diversification Score: {div_score:.2f}/1.0
Portfolio Value: ${portfolio_val:,.0f}
Number of Holdings: {holdings_count}

Concentration Risks: {state.get('portfolio_concentration_risks', [])}

Explain what this composition tells us about the portfolio strategy and diversification.
Use simple language a non-expert investor would understand.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="interpretation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error interpreting portfolio: {str(e)}")
            return "Portfolio composition could not be interpreted."
    
    async def _interpret_risk_metrics(self, state: AnalysisState) -> str:
        """Interpret risk metrics and risk level"""
        try:
            sharpe = state.get('sharpe_ratio') or 0
            volatility = state.get('volatility') or 0
            beta = state.get('beta') or 1.0
            max_dd = state.get('max_drawdown') or 0
            
            prompt = f"""
Explain these risk metrics in plain English (2-3 sentences):

Risk Level: {state.get('risk_level', 'Moderate')}
Sharpe Ratio: {sharpe:.2f} (higher = better risk-adjusted returns)
Volatility: {volatility:.2%} annual (chance of year-to-year price swings)
Beta: {beta:.2f} (1.0 = moves with market, <1 = less volatile, >1 = more volatile)
Max Drawdown: {max_dd:.2%} (worst loss from peak)
User Risk Profile: {state.get('risk_profile', 'unknown')}

Explain what these numbers mean and whether they match the user's {state.get('risk_profile', 'unknown')} risk tolerance.
Use simple language for non-experts.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="interpretation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error interpreting risk: {str(e)}")
            return "Risk metrics could not be interpreted."
    
    async def _interpret_allocation_shift(self, state: AnalysisState) -> str:
        """Interpret the shift from current to recommended allocation"""
        try:
            current = state.get('allocation', {})
            target = state.get('recommended_allocation', {})
            
            prompt = f"""
Explain the recommended allocation change in simple terms (2-3 sentences):

Current Allocation: {current}
Recommended Allocation: {target}
Risk Profile: {state.get('risk_profile', 'moderate')}
Projected Sharpe Improvement: {state.get('sharpe_ratio', 0):.2f} → {state.get('projected_sharpe', 0):.2f}

Explain why this rebalancing makes sense for a {state.get('risk_profile', 'moderate')} investor.
Focus on the benefits, not the technical details.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="interpretation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error interpreting allocation shift: {str(e)}")
            return "Allocation shift could not be interpreted."
    
    async def _interpret_opportunities(self, state: AnalysisState) -> str:
        """Identify and explain key opportunities"""
        try:
            prompt = f"""
Identify 2-3 key opportunities or issues with this portfolio:

Current Diversification: {state.get('diversification_score', 0):.2f}/1.0
Concentration Risks: {state.get('portfolio_concentration_risks', [])}
Compliance Violations: {state.get('compliance_violations', [])}
Current Sharpe Ratio: {state.get('sharpe_ratio', 0):.2f}
Projected Sharpe Ratio: {state.get('projected_sharpe', 0):.2f}

Summarize the top 2-3 actionable insights from the analysis in 2-3 sentences.
Make it clear what the investor should pay attention to.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="interpretation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error identifying opportunities: {str(e)}")
            return "Opportunities could not be identified."
