"""
Recommendation Rationale Agent (Post-Analysis)

Responsibility:
- Explain why specific recommendations make sense
- Connect recommendations to metrics and user goals
- Generate detailed rationale for each trade
- Help user understand the 'why' behind suggestions
"""

import logging
from typing import Dict, Any, Optional, List
from app.agents.state import AnalysisState
from app.services.llm_wrapper import LLMWrapper

logger = logging.getLogger(__name__)


class RecommendationRationaleAgent:
    """
    Post-analysis agent that explains recommendations with metrics-based rationale
    
    Input: All computed metrics + recommended trades from Agent 3
    Output: Detailed explanations of why each recommendation makes sense
    """
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None):
        """Initialize agent"""
        self.llm = llm_wrapper or LLMWrapper(model_name="openai/gpt-oss-120b")
        self.logger = logger
    
    async def generate_rationale(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Generate detailed rationale for all recommendations
        
        Args:
            state: Complete analysis state with metrics and recommendations
            
        Returns:
            Dictionary with overall rationale and per-trade rationales
        """
        try:
            result = {}
            
            # Overall rationale explaining the strategy
            result["overall_strategy"] = await self._explain_strategy(state)
            
            # Per-trade rationales using ACTUAL trade data
            trades = state.get("rebalancing_trades", [])
            result["trade_rationales"] = []
            for trade in trades[:10]:  # Limit to top 10 trades
                rationale = await self._explain_trade(state, trade)
                result["trade_rationales"].append({
                    "action": trade.get("action"),
                    "ticker": trade.get("ticker"),
                    "quantity_change": trade.get("quantity_change"),  # ACTUAL field name
                    "trade_value": trade.get("trade_value"),  # ACTUAL field name
                    "current_price": trade.get("current_price"),  # ACTUAL field name
                    "reason": trade.get("reason"),  # Use the reason from trade
                    "rationale": rationale,
                })
            
            # Benefits and tax considerations
            result["benefits"] = await self._explain_benefits(state)
            result["tax_considerations"] = await self._explain_tax_implications(state)
            result["implementation_guide"] = await self._explain_implementation(state)
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error generating rationale: {str(e)}")
            return {"error": f"Could not generate rationale: {str(e)}"}
    
    async def _explain_strategy(self, state: AnalysisState) -> str:
        """Explain the overall rebalancing strategy with specific impact metrics"""
        try:
            current = state.get("allocation", {})
            target = state.get("recommended_allocation", {})
            risk_profile = state.get("risk_profile", "moderate")
            trades = state.get("rebalancing_trades", [])
            household_income = state.get("household_income", 0)
            cash_on_hand = state.get("cash_on_hand", 0)
            monthly_investable_income = state.get("monthly_investable_income", 0)
            implementation_scenario = state.get("implementation_scenario", "phased_12m")
            portfolio_value = state.get("portfolio_value", 0)
            
            # Summarize key trades
            buy_trades = [t for t in trades if t.get('action') == 'buy']
            sell_trades = [t for t in trades if t.get('action') == 'sell']
            total_buy_value = sum([t.get('trade_value', 0) for t in buy_trades])
            
            # Build trade summaries
            buy_tickers = [f"{t.get('quantity_change', 0):.0f} {t.get('ticker')}" for t in buy_trades[:3]]
            buy_summary = f"Buy {len(buy_trades)} position(s): {', '.join(buy_tickers)}"
            sell_summary = f"Sell {len(sell_trades)} position(s)" if sell_trades else "No sales needed"
            
            # Funding capacity assessment
            funding_guidance = ""
            if implementation_scenario == "immediate" and cash_on_hand >= total_buy_value:
                funding_guidance = f"With available cash of ${cash_on_hand:,.0f}, the full ${total_buy_value:,.0f} rebalancing can be executed immediately."
            elif implementation_scenario == "phased_12m":
                months_to_fund = int(total_buy_value / max(monthly_investable_income, 1))
                funding_guidance = f"With monthly savings of ${monthly_investable_income:,.0f}, the rebalancing can be completed in approximately {months_to_fund} months."
            elif implementation_scenario == "requires_liquidation":
                shortfall = total_buy_value - cash_on_hand
                funding_guidance = f"With ${cash_on_hand:,.0f} available and ${monthly_investable_income:,.0f}/month capacity, consider liquidating low-conviction positions (${shortfall:,.0f} shortfall) to fund the complete rebalancing immediately."
            
            prompt = f"""
Provide a comprehensive 5-6 sentence explanation of the rebalancing strategy. IMPORTANT: Include actual cash availability and funding capacity.

CURRENT STATE:
- Current Allocation: {current}
- Current Diversification Score: {state.get('diversification_score', 0):.2f} / 1.0
- Current Sharpe Ratio: {state.get('sharpe_ratio', 0):.2f}
- Current Volatility: {state.get('volatility', 0):.2%}
- Portfolio Value: ${portfolio_value:,.0f}
- Client Risk Profile: {risk_profile}

FINANCIAL CAPACITY:
- Liquid Cash Available: ${cash_on_hand:,.0f}
- Monthly Investable Income: ${monthly_investable_income:,.0f}
- Annual Household Income (salary): ${household_income:,.0f}
- Implementation Scenario: {implementation_scenario}

TARGET STATE:
- Target Allocation: {target}
- Target Diversification Score: ~1.0 (perfectly diversified)
- Projected Sharpe Ratio: {state.get('projected_sharpe', 0):.2f}
- Projected Volatility: {state.get('projected_volatility', 0):.2%}
- Projected Annual Return: {state.get('projected_return', 0.07):.2%}

KEY ACTIONS:
{buy_summary}
{sell_summary}
Total Cash Needed for Purchases: ${total_buy_value:,.0f}

FUNDING STRATEGY:
{funding_guidance}

EXPECTED BENEFITS:
- Implementation Cost: ${state.get('implementation_cost', 0):,.0f} ({(state.get('implementation_cost', 0)/portfolio_value)*100:.2f}% of portfolio)
- Tax Impact: ${state.get('tax_impact', 0):,.0f}
- Sharpe Ratio Improvement: {state.get('sharpe_ratio', 0):.2f} → {state.get('projected_sharpe', 0):.2f}
- Risk-Return Efficiency Gain: {((state.get('projected_sharpe', 0) / max(state.get('sharpe_ratio', 0.1), 0.1)) - 1) * 100:.1f}%

Explain how this strategy aligns with the {risk_profile} risk profile by moving from concentrated to diversified allocation.
Clearly address how the available liquid cash (${cash_on_hand:,.0f}) and monthly savings (${monthly_investable_income:,.0f}) enable the rebalancing.
The implementation scenario is "{implementation_scenario}" - adjust your explanation to reflect this funding pathway.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="recommendation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error explaining strategy: {str(e)}")
            return "Strategy explanation unavailable."
    
    async def _explain_trade(self, state: AnalysisState, trade: Dict[str, Any]) -> str:
        """Explain rationale for a specific trade using ACTUAL trade data"""
        try:
            action = trade.get('action', '?').upper()
            ticker = trade.get('ticker', '?')
            quantity_change = trade.get('quantity_change', 0)
            trade_value = trade.get('trade_value', 0)
            current_price = trade.get('current_price', 0)
            reason = trade.get('reason', 'Target allocation')
            current_quantity = trade.get('current_quantity', 0)
            target_quantity = trade.get('target_quantity', 0)
            
            # Construct detailed prompt with actual trade data
            prompt = f"""
Explain why this specific trade makes sense for a {state.get('risk_profile', 'moderate')} investor (2-3 sentences):

TRADE DETAILS:
- Action: {action} {quantity_change:.2f} shares of {ticker}
- Current Quantity: {current_quantity:.2f} shares
- Target Quantity: {target_quantity:.2f} shares
- Price per Share: ${current_price:.2f}
- Total Trade Value: ${trade_value:,.2f}
- Stated Reason: {reason}

PORTFOLIO CONTEXT:
- Current Diversification Score: {state.get('diversification_score', 0):.2f} / 1.0 (where 1.0 is perfectly diversified)
- Current Volatility: {state.get('volatility', 0):.2%} annually
- Expected Volatility After: {state.get('projected_volatility', 0):.2%} 
- Sharpe Ratio Improvement: {state.get('sharpe_ratio', 0):.2f} → {state.get('projected_sharpe', 0):.2f}
- Client Risk Profile: {state.get('risk_profile', 'moderate')}

IMPROVEMENT METRICS:
- Expected 1-Year Return: {state.get('projected_return', 0.07):.2%}
- Concentration Risk Change: {state.get('concentration_risk', 0):.2%} (lower is better)
- Tax Impact: ${state.get('tax_impact', 0):,.0f} (0 or negative is good)

Provide a clear, compelling explanation linking this specific trade to the investor's risk profile and expected improvements.
Mention the impact on portfolio diversification and risk-adjusted returns. Be specific about dollar amounts and percentages.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="recommendation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error explaining trade: {str(e)}")
            return f"Trade rationale unavailable for {trade.get('action', '?')} {trade.get('ticker', '?')}."
    
    async def _explain_benefits(self, state: AnalysisState) -> str:
        """Explain the concrete benefits of rebalancing with specific impact metrics"""
        try:
            sharpe_improvement = state.get('projected_sharpe', 0) - state.get('sharpe_ratio', 0)
            volume_improvement = state.get('projected_volatility', 0) / max(state.get('volatility', 0.1), 0.1)
            diversification_improvement = 1.0 - state.get('diversification_score', 0.5)
            
            prompt = f"""
Provide a detailed 4-5 sentence explanation of the specific benefits of rebalancing:

CURRENT PORTFOLIO:
- Risk Level: {state.get('risk_level', 'Unknown')} (from current metrics)
- Diversification: {state.get('diversification_score', 0):.1%} (where 100% = perfectly diversified)
- Sharpe Ratio: {state.get('sharpe_ratio', 0):.2f} (risk-adjusted return efficiency)
- Volatility: {state.get('volatility', 0):.2%} (annual price swings)
- Maximum Historical Drawdown: {state.get('max_drawdown', 0):.2%} (worst loss from peak)

AFTER REBALANCING:
- Projected Risk Level: Reduced to Moderate
- Diversification: Improved to ~100% (much better spread)
- Sharpe Ratio: {state.get('projected_sharpe', 0):.2f} (+{sharpe_improvement:.2f} improvement)
- Projected Volatility: {state.get('projected_volatility', 0):.2%} 
- Expected Annual Return: {state.get('projected_return', 0.07):.2%}

FINANCIAL IMPACT:
- Effort Cost: ${state.get('implementation_cost', 0):,.0f} ({(state.get('implementation_cost', 0) / max(state.get('portfolio_value', 1), 1)) * 100:.2f}% of portfolio)
- Tax Cost: ${state.get('tax_impact', 0):,.0f}
- No Long-Term Cost – Plan to hold for at least 3+ years
- Portfolio Value: ${state.get('portfolio_value', 0):,.0f}

Explain why the {sharpe_improvement:.2f} point improvement in Sharpe ratio is significant.
Discuss how reducing portfolio volatility by {abs(1-volume_improvement)*100:.1f}% reduces the risk of catastrophic losses.
Address whether the ${state.get('implementation_cost', 0):,.0f} cost is justified by these improvements.
Emphasize that this rebalancing is a one-time action aligned with a {state.get('risk_profile', 'moderate')} risk appetite
and an annual household income of ${state.get('household_income', 0):,.0f}.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="recommendation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error explaining benefits: {str(e)}")
            return "Benefits explanation unavailable."
    
    async def _explain_tax_implications(self, state: AnalysisState) -> str:
        """Explain tax and cash-sourcing implications of rebalancing"""
        try:
            impl_cost = state.get('implementation_cost', 0)
            tax_impact = state.get('tax_impact', 0)
            total_cost = impl_cost + abs(tax_impact if tax_impact < 0 else 0)
            portfolio_value = state.get("portfolio_value", 1)
            household_income = state.get("household_income", 0)
            cash_on_hand = state.get("cash_on_hand", 0)
            monthly_investable_income = state.get("monthly_investable_income", 0)
            implementation_scenario = state.get("implementation_scenario", "phased_12m")
            trades = state.get("rebalancing_trades", [])
            buy_trades = [t for t in trades if t.get('action') == 'buy']
            total_buy_value = sum([t.get('trade_value', 0) for t in buy_trades])
            
            cost_as_pct = (total_cost / portfolio_value) * 100
            
            expected_benefit = state.get('projected_return', 0.07) - state.get('sharpe_ratio', 0.7) * 0.05
            breakeven_months = (total_cost / (portfolio_value * expected_benefit / 12)) if expected_benefit > 0 else 999
            
            # Assessment of funding capacity
            funding_summary = ""
            if implementation_scenario == "immediate":
                funding_summary = f"With liquid cash of ${cash_on_hand:,.0f}, funding the ${total_buy_value:,.0f} rebalancing is achievable immediately."
            elif implementation_scenario == "phased_12m":
                funding_summary = f"With ${cash_on_hand:,.0f} available now and ${monthly_investable_income:,.0f}/month savings capacity, rebalancing can be phased over 12 months."
            elif implementation_scenario == "requires_liquidation":
                shortfall = total_buy_value - cash_on_hand
                funding_summary = f"The rebalancing requires ${total_buy_value:,.0f} but only ${cash_on_hand:,.0f} is immediately available. Liquidate ${shortfall:,.0f} of low-conviction positions (prioritizing losses for tax harvesting) and use ${monthly_investable_income:,.0f}/month savings to complete the transition."
            
            prompt = f"""
Provide a detailed 5-6 sentence cost-benefit analysis of the rebalancing from a tax and cash-sourcing perspective.

COSTS OF REBALANCING:
- Implementation/Trading Costs: ${impl_cost:,.0f}
- Estimated Tax Impact: ${tax_impact:,.0f}
- Total Cost: ${total_cost:,.0f}
- Cost as % of Portfolio: {cost_as_pct:.2f}%

FINANCIAL METRICS:
- Current Portfolio Value: ${portfolio_value:,.0f}
- Current Annual Expected Return: {(state.get('sharpe_ratio', 0.7) * 0.07):.2%}
- Projected Annual Expected Return: {state.get('projected_return', 0.07):.2%}
- Expected Annual Profit Increase: ${((state.get('projected_return', 0.07) - state.get('sharpe_ratio', 0.7) * 0.07) * portfolio_value):,.0f}
- Estimated Breakeven Time: {breakeven_months:.1f} months (cost recovery period)

AVAILABLE LIQUIDITY:
- Liquid Cash on Hand: ${cash_on_hand:,.0f}
- Monthly Investable Income (after expenses): ${monthly_investable_income:,.0f}
- Annual Household Income (salary): ${household_income:,.0f}
- CRITICAL DISTINCTION: The ${household_income:,.0f} is YOUR SALARY (recurring monthly), NOT a cash pool available today

FUNDING CAPACITY:
{funding_summary}
Total Required for Full Rebalancing: ${total_buy_value:,.0f}

TAX CONTEXT:
- Risk Profile: {state.get('risk_profile', 'moderate')}
- Long-term Capital Gains Tax Rate: ~15-20% (federal + state)
- Note: Tax impact (${tax_impact:,.0f}) assumes cost-basis treatment; actual depends on your holdings

RECOMMENDATION:
For a {state.get('risk_profile', 'moderate')} investor with ${household_income:,.0f} annual income and ${portfolio_value:,.0f} portfolio,
the ${total_cost:,.0f} rebalancing cost breaks even within {breakeven_months:.1f} months of improved returns.
You have ${cash_on_hand:,.0f} in available cash and ${monthly_investable_income:,.0f}/month in additional capacity.
Implementation scenario: "{implementation_scenario}" - prioritize tax-loss harvesting on any underwater positions.
If liquidating positions to fund the purchase, sell losses first (tax shield), then lowest-conviction holdings.
The phased approach (monthly from salary) is conservative: ${monthly_investable_income:,.0f}/month × 12 months = funding pathway viable for moderate-risk investors.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="recommendation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error explaining tax implications: {str(e)}")
            return "Tax implications explanation unavailable."
    
    async def _explain_implementation(self, state: AnalysisState) -> str:
        """Explain how to implement recommendations with specific actions"""
        try:
            trades = state.get("rebalancing_trades", [])
            buy_trades = [t for t in trades if t.get('action') == 'buy']
            sell_trades = [t for t in trades if t.get('action') == 'sell']
            
            total_buy_value = sum([t.get('trade_value', 0) for t in buy_trades])
            total_sell_value = sum([t.get('trade_value', 0) for t in sell_trades])
            portfolio_value = state.get("portfolio_value", 1)
            household_income = state.get("household_income", 0)
            cash_on_hand = state.get("cash_on_hand", 0)
            monthly_investable_income = state.get("monthly_investable_income", 0)
            implementation_scenario = state.get("implementation_scenario", "phased_12m")
            
            # Build trade details
            buy_details = [f"{t.get('ticker')}: {t.get('quantity_change', 0):.0f} shares @ ${t.get('current_price', 0):.2f}" for t in buy_trades[:3]]
            buy_list = ', '.join(buy_details) if buy_details else "No buy trades"
            
            # Calculate if adequate cash exists (this is critical!)
            net_cash_needed = total_buy_value - total_sell_value
            
            # Instruction based on funding scenario
            scenario_instruction = ""
            if implementation_scenario == "immediate":
                scenario_instruction = f"You have ${cash_on_hand:,.0f} available, which covers the ${net_cash_needed:,.0f} required. Execute immediately in 1-2 weeks."
            elif implementation_scenario == "phased_12m":
                scenario_instruction = f"With ${cash_on_hand:,.0f} on hand and ${monthly_investable_income:,.0f}/month savings, execute in phases over ~12 months. Buy ${net_cash_needed/12:,.0f} worth monthly."
            elif implementation_scenario == "requires_liquidation":
                shortfall = net_cash_needed - cash_on_hand
                scenario_instruction = f"You have ${cash_on_hand:,.0f} but need ${net_cash_needed:,.0f}. Liquidate ${shortfall:,.0f} of low-conviction positions (prioritize losses for tax harvesting), then execute purchases. Timeline: 2-4 weeks."
            
            prompt = f"""
Provide a detailed 5-6 sentence implementation guide for executing this rebalancing. Include specific cash-sourcing strategy.

PORTFOLIO CONTEXT:
- Total Portfolio Value: ${portfolio_value:,.0f}
- Liquid Cash on Hand: ${cash_on_hand:,.0f}
- Monthly Investable Capacity: ${monthly_investable_income:,.0f}
- Annual Household Income: ${household_income:,.0f}
- Risk Profile: {state.get('risk_profile', 'moderate')}
- IMPORTANT: The ${household_income:,.0f} annual income is SALARY (recurring), not immediate cash for investing

EXECUTION PLAN:
- Total Trades: {len(trades)} transactions
- Buy Transactions: {len(buy_trades)} ({buy_list})
- Sell Transactions: {len(sell_trades)} (if any)
- Net Cash Requirement: ${net_cash_needed:,.0f}
- Total Implementation Cost: ${state.get('implementation_cost', 0):,.0f}

FUNDING STRATEGY ({implementation_scenario}):
{scenario_instruction}

CASH SOURCING:
Current available cash: ${cash_on_hand:,.0f}
Shortfall (if any): ${max(0, net_cash_needed - cash_on_hand):,.0f}
Monthly savings from income: ${monthly_investable_income:,.0f}

Provide concrete implementation steps:
1. Confirm account cash balance and whether it matches $ {cash_on_hand:,.0f}
2. If liquidating positions, identify those with losses first (tax harvesting) or lowest-conviction holdings
3. Place limit orders for each buy (KO, T, BND, VNQ) in batches of 2 over 2 days to manage execution
4. Monitor fills daily and adjust limits if needed
5. Record trade dates, prices, and proceeds for tax filing
6. Schedule post-execution review (1-2 weeks out) and annual rebalancing checkpoint
The implementation timeline is {implementation_scenario} - pace execution accordingly.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                use_case="recommendation",
                temperature=0.6,
            )
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error explaining implementation: {str(e)}")
            return "Implementation guidance unavailable."
