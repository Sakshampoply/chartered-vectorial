"""
Prompt templates for Advisor Copilot Agent

Handles:
- Explaining analysis results
- Answering questions about recommendations
- What-if scenario discussions
- Investment thesis generation
"""

ADVISOR_COPILOT_SYSTEM_PROMPT = """You are an expert financial advisor assistant. Your role is to help advisors understand portfolio analysis results and answer client questions about investment recommendations.

IMPORTANT RULES:
1. You NEVER recompute financial metrics. You interpret results provided by the system.
2. You only explain analysis findings, never create new calculations.
3. Always cite specific metrics from the analysis when explaining.
4. Use simple, client-friendly language - avoid unnecessary jargon.
5. Provide confidence levels when uncertain about recommendations.

Available context:
- Portfolio composition and allocations
- Risk metrics (Sharpe ratio, volatility, beta, max drawdown)
- Identified concentration risks
- Recommended allocation changes
- Projected returns and scenarios
- Implementation costs and tax implications
- Feasibility and impact scores

Your responsibilities:
1. Answer "Why?" questions about the analysis
2. Explain trade-offs in recommendations
3. Discuss implementation considerations
4. Address advisor/client concerns
5. Support decision-making conversations

Always reference the actual numbers and explain reasoning clearly."""

EXPLANATION_TEMPLATE = """Based on the portfolio analysis, here's what we found:

**Current State:**
{current_situation}

**Key Finding:**
{finding}

**Why This Matters:**
{significance}

**What We Recommend:**
{recommendation}

**Expected Outcome:**
{projected_outcome}

**Implementation Consideration:**
{implementation_notes}"""

WHAT_IF_TEMPLATE = """If we adjust the portfolio allocation to {scenario_change}:

**New Allocation:**
{new_allocation}

**Projected Impact:**
- Expected Return: {projected_return}% (from {current_return}%)
- Volatility: {projected_volatility}% (from {current_volatility}%)
- Sharpe Ratio: {projected_sharpe} (from {current_sharpe})
- Max Drawdown: {projected_max_dd}% (from {current_max_dd}%)

**Advantages:**
{advantages}

**Disadvantages:**
{disadvantages}

**Implementation Cost:** ${implementation_cost:,.0f}
**Tax Impact:** ${tax_impact:,.0f}"""

RISK_EXPLANATION_TEMPLATE = """Your client's current risk profile shows:

**Overall Risk Level:** {risk_level} ({risk_score}/5)

**Key Metrics:**
- Annual Volatility: {volatility}% (how much the portfolio swings year-to-year)
- Beta: {beta} (sensitivity to market movements)
- Sharpe Ratio: {sharpe_ratio} (risk-adjusted return quality)
- Maximum Drawdown: {max_drawdown}% (worst historical loss)

**What This Means:**
{risk_interpretation}

**In Practical Terms:**
- If the market drops 10%, this portfolio would likely drop ~{expected_loss}%
- In a year with average returns, expect {typical_return_range}% return
- Worst historical loss period would lose ~{max_loss}%

**Is This Aligned With Their Goals?**
{alignment_assessment}"""

TAX_EFFICIENCY_TEMPLATE = """Regarding tax implications of this recommendation:

**Potential Tax Issues:**
{current_tax_issues}

**Short-term vs Long-term:**
- Holdings held > 1 year: {long_term_percentage}% (favorable tax treatment)
- Holdings < 1 year: {short_term_percentage}% (taxed as ordinary income)

**Implementation Strategy:**
{tax_strategy}

**Estimated Tax Cost:** ${estimated_tax:,.0f}
**Tax-Loss Harvesting Opportunities:** ${tax_loss_harvesting:,.0f}

**Net Benefit After Tax:** ${net_benefit:,.0f}"""

CONCENTRATION_RISK_EXPLANATION = """I notice your portfolio has a concentration risk that warrants discussion:

**Current Concentration:**
{concentration_description}

**Why This Is a Risk:**
{concentration_risk}

**Real-World Example:**
{historical_example}

**Our Recommendation:**
{diversification_strategy}

**Expected Diversification Improvement:**
- Concentration Risk Index: {current_cri} → {target_cri}
- Largest Position: {current_largest}% → {target_largest}%
- Top 3 Holdings Exposure: {current_top3}% → {target_top3}%"""

PERFORMANCE_PROJECTION_TEMPLATE = """Based on historical analysis, here's what we project:

**1-Year Projection:**
- Base Case: ${current_value:,.0f} → ${projection_1yr:,.0f}
- Best Case (75th percentile): ${best_1yr:,.0f}
- Worst Case (25th percentile): ${worst_1yr:,.0f}

**3-Year Projection:**
- Base Case: ${current_value:,.0f} → ${projection_3yr:,.0f}
- Best Case: ${best_3yr:,.0f}
- Worst Case: ${worst_3yr:,.0f}

**Important Notes:**
- These are NOT guarantees, just statistical estimates
- Actual returns will vary based on market conditions
- Regular rebalancing helps maintain target allocation
- Dollar-cost averaging into positions reduces timing risk"""

COPILOT_TOOLS_SCHEMA = {
    "type": "object",
    "properties": {
        "portfolio_holdings": {
            "type": "object",
            "description": "Current holdings and allocations"
        },
        "risk_metrics": {
            "type": "object",
            "description": "Calculated risk metrics"
        },
        "recommendations": {
            "type": "object",
            "description": "Portfolio optimization results"
        },
        "scores": {
            "type": "object",
            "description": "Feasibility and impact scores"
        },
        "client_profile": {
            "type": "object",
            "description": "Client goals and preferences"
        }
    },
    "description": "Available context for copilot reasoning"
}
