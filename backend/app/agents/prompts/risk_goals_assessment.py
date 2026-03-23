"""
Prompt templates for Risk & Goals Assessment Agent (Stage 2 - Minimal Questioning)

Replaces the lengthy ChatIntakeAgent + RiskProfilerAgent with 2-3 essential questions only:
1. Risk tolerance level (REQUIRED)
2. Annual household income (REQUIRED)  
3. Primary goal (OPTIONAL)

All other information (age, timeline, employment, goals) are extracted from Stage 1 documents.
"""

RISK_GOALS_SYSTEM_PROMPT = """You are a focused investment advisor gathering ONLY the 2-3 critical pieces of missing information for investment analysis.

QUESTIONS TO ASK (in order):
1. **Risk Tolerance** (REQUIRED): "What is your risk tolerance level: conservative (stable, low growth), moderate (balanced, some volatility), or aggressive (growth-focused, higher volatility)?"
2. **Household Income** (REQUIRED): "What is your approximate annual household income?"
3. **Primary Goal** (OPTIONAL): "What is your primary investment goal: retirement, growth, income generation, or education funding?"

IMPORTANT RULES:
- Ask ONLY the required questions. Do not ask other questions.
- Be concise and professional
- Accept responses naturally (e.g., "I'm moderate risk" or "Around $150k per year")
- After collecting both required fields, offer to proceed to analysis
- If they skip the optional question, proceed to analysis anyway

STYLE:
- Professional but friendly
- Direct and efficient (no long preambles)
- Acknowledge each answer before moving to the next question
"""

RISK_GOALS_QUESTION_1 = """To better tailor the investment analysis, I need to understand your risk tolerance.

**What is your preferred risk level?**
- **Conservative**: Prioritize capital preservation, modest growth, minimal volatility (e.g., 40% stocks / 60% bonds)
- **Moderate**: Balance growth with stability, accept some year-to-year fluctuation (e.g., 60% stocks / 40% bonds)
- **Aggressive**: Maximize long-term growth, comfortable with significant short-term volatility (e.g., 80%+ stocks)

Which best describes your comfort level?"""

RISK_GOALS_QUESTION_2 = """Thank you! Now I need one more key piece of information.

**What is your approximate annual household income?**
(This helps us understand your investment capacity and cash flow needs. Just a range is fine: e.g., $100k, $250k, etc.)"""

RISK_GOALS_QUESTION_3 = """Great! One optional quick question:

**What is your primary investment goal?**
- Retirement planning
- Wealth growth
- Income generation
- Education funding
- Other

(You can skip this if you prefer—we can proceed with the analysis either way.)"""

EXTRACT_RISK_GOALS_SCHEMA = {
    "type": "object",
    "properties": {
        "response_to_user": {
            "type": "string",
            "description": "Conversational response to user, next question, or completion message"
        },
        "extracted_info": {
            "type": "object",
            "description": "Information extracted in this message",
            "properties": {
                "risk_tolerance": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive", "unknown"],
                    "description": "Client's risk tolerance level"
                },
                "household_income": {
                    "type": "number",
                    "description": "Annual household income in USD (null if not yet asked)"
                },
                "primary_goal": {
                    "type": "string",
                    "description": "Primary investment goal (retirement/growth/income/education/other)",
                    "enum": ["retirement", "growth", "income", "education", "other", "unknown"]
                }
            }
        },
        "completion_status": {
            "type": "object",
            "description": "Stage 2 completion tracking",
            "properties": {
                "has_risk_tolerance": {"type": "boolean"},
                "has_household_income": {"type": "boolean"},
                "has_primary_goal": {"type": "boolean"},
                "info_collection_complete": {
                    "type": "boolean",
                    "description": "True if both required fields filled (risk tolerance + household income)"
                },
                "progress_percent": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Progress: 33% for Q1, 67% for Q2, 100% for Q3 or skip Q3"
                }
            }
        }
    },
    "required": ["response_to_user", "extracted_info", "completion_status"]
}

COMPLETION_MESSAGE_TEMPLATE = """Perfect! I now have everything needed for the analysis:

**Your Investment Profile:**
- Risk Tolerance: {risk_tolerance}
- Household Income: ${household_income:,.0f}/year
{primary_goal_text}

Let me now analyze your portfolio. This will take 15-20 seconds as three specialized AI agents examine your holdings, assess risk, and generate recommendations.

Starting analysis..."""

SKIP_OPTIONAL_QUESTION = """Got it! We have everything we need to proceed. Let me start the portfolio analysis:

**Your Investment Profile:**
- Risk Tolerance: {risk_tolerance}
- Household Income: ${household_income:,.0f}/year

Starting analysis (15-20 seconds)..."""
