"""
Prompt templates for Risk Profiling Agent

Handles:
- Progressive risk assessment questions
- Risk tolerance evaluation
- Investment goal clarification
"""

RISK_PROFILING_SYSTEM_PROMPT = """You are a financial advisor conducting a risk assessment interview. Your role is to understand the client's risk tolerance and investment objectives.

Guidelines:
1. Ask questions in a natural, conversational way
2. Avoid jargon - explain financial terms simply
3. Listen for concerns and follow up appropriately
4. Build rapport and trust
5. Be empathetic about financial concerns

Real risk tolerance comes from understanding:
- Their past investment experience
- How they react to market volatility
- Their financial needs and timeline
- Their emotional comfort with risk
- Their income stability and emergency funds

Always validate their responses and confirm understanding before moving to the next question."""

RISK_QUESTIONS = [
    {
        "sequence": 1,
        "question": "What is your primary investment goal for this portfolio? (For example: retirement income, wealth growth, education funding, or wealth preservation)",
        "field": "investment_goal",
        "category": "goals"
    },
    {
        "sequence": 2,
        "question": "When do you plan to need significant money from this portfolio? (In years)",
        "field": "investment_horizon",
        "category": "timeline"
    },
    {
        "sequence": 3,
        "question": "Have you experienced a significant market downturn before (like 2008 or 2020)? How did you feel about it?",
        "field": "market_experience",
        "category": "experience"
    },
    {
        "sequence": 4,
        "question": "If this portfolio temporarily lost 30% of its value, would you be comfortable holding and waiting for recovery, or would you feel pressured to sell?",
        "field": "volatility_tolerance",
        "category": "risk_tolerance"
    },
    {
        "sequence": 5,
        "question": "Do you have an emergency fund separate from this portfolio? (3-6 months of expenses)",
        "field": "emergency_fund",
        "category": "financial_health"
    },
    {
        "sequence": 6,
        "question": "Will you need to withdraw funds from this portfolio regularly, or can it grow untouched for years?",
        "field": "liquidity_needs",
        "category": "cash_flows"
    },
    {
        "sequence": 7,
        "question": "Are you concerned about inflation eroding your purchasing power, or is capital preservation more important?",
        "field": "inflation_concern",
        "category": "priorities"
    },
    {
        "sequence": 8,
        "question": "On a scale of 1-10, how would you rate your investment knowledge? (1=beginner, 10=expert)",
        "field": "investment_knowledge",
        "category": "experience"
    }
]

RISK_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "investment_goal": {
            "type": "string",
            "description": "Primary investment goal"
        },
        "investment_horizon": {
            "type": "integer",
            "description": "Years until funds needed"
        },
        "market_experience": {
            "type": "string",
            "description": "Past market experience level"
        },
        "volatility_tolerance": {
            "type": "string",
            "enum": ["very_low", "low", "moderate", "high", "very_high"],
            "description": "Comfort with portfolio volatility"
        },
        "emergency_fund": {
            "type": "boolean",
            "description": "Has emergency fund"
        },
        "liquidity_needs": {
            "type": "string",
            "enum": ["none", "some", "regular"],
            "description": "Need for regular withdrawals"
        },
        "inflation_concern": {
            "type": "string",
            "enum": ["capital_preservation", "moderate", "growth_focused"],
            "description": "Inflation vs preservation priority"
        },
        "investment_knowledge": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Self-rated investment knowledge"
        }
    }
}

# Scoring rules for risk profile
RISK_SCORE_MAPPING = {
    "volatility_tolerance": {
        "very_low": 1,
        "low": 2,
        "moderate": 3,
        "high": 4,
        "very_high": 5,
    },
    "investment_horizon": {
        "less_than_2": 1,
        "2_5": 2,
        "5_10": 3,
        "10_20": 4,
        "more_than_20": 5,
    },
    "market_experience": {
        "none": 1,
        "some_bearish": 2,
        "some_bullish": 3,
        "experienced": 4,
        "very_experienced": 5,
    }
}

RISK_CATEGORY_MAPPING = {
    "low": {"min": 0, "max": 1.5, "label": "Conservative", "allocation": "bonds_heavy"},
    "moderate": {"min": 1.5, "max": 2.8, "label": "Moderate", "allocation": "balanced"},
    "high": {"min": 2.8, "max": 4.0, "label": "Growth", "allocation": "equity_heavy"},
    "very_high": {"min": 4.0, "max": 5.0, "label": "Aggressive", "allocation": "equity_focused"},
}
