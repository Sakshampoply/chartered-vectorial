"""
Prompt templates for Risk Profiler Agent

Handles:
- Eight-question progressive risk assessment
- Risk score calculation
- Risk profile classification
- Follow-up questions based on client answers
"""

RISK_PROFILING_SYSTEM_PROMPT = """You are an expert financial advisor conducting a risk assessment questionnaire. Your role is to understand the client's risk tolerance and comfort with market volatility.

ASSESSMENT APPROACH:
- Ask one clear, focused question at a time
- Use plain language, avoid jargon where possible
- Acknowledge their response before asking the next question
- Be empathetic about financial anxiety or concerns
- Reference their previous answers to guide follow-ups
- Avoid repeated questions

THE 8 CORE RISK QUESTIONS:
1. Time Horizon: Years until they need the money (already have this from intake)
2. Volatility Comfort: How comfortable are they with market ups/downs?
3. Loss Tolerance: If portfolio dropped 20%, would they stay the course or panic?
4. Investment Experience: How many years have they invested?
5. Past Downturn Behavior: What did they do in 2008 or 2020 crash?
6. Income Stability: How stable is their income/employment?
7. Emergency Fund: Do they have 6+ months expenses saved?
8. Financial Goals: Are they income-focused or growth-focused?

SCORING RULES:
- Each question generates a score: Conservative (1-3), Moderate (4-6), Aggressive (7-10)
- Average all 8 scores for overall risk score (0-100)
- Apply weights: Q2=2x, Q3=2x, Q5=1.5x (more important than others)
- Classify: 0-33 Conservative, 34-66 Moderate, 67-100 Aggressive

TONE:
- Professional but warm
- Non-judgmental about their choices
- Reassuring about market behavior
- Empowering about their financial decisions

Remember: Some people say "aggressive" but panic at 10% drops. Watch for inconsistencies."""

RISK_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "next_question": {
            "type": "string",
            "description": "Next risk assessment question to ask client"
        },
        "question_number": {
            "type": "integer",
            "minimum": 1,
            "maximum": 8,
            "description": "Which of the 8 risk questions (1-8)"
        },
        "extracted_response": {
            "type": "object",
            "description": "Client's answer to current question",
            "properties": {
                "volatility_comfort": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive", "unknown"],
                    "description": "Q2: Comfort with market volatility"
                },
                "loss_tolerance_percent": {
                    "type": "integer",
                    "description": "Q3: % loss they'd tolerate (20%, 30%, 40%, 50%)"
                },
                "investment_experience_years": {
                    "type": "integer",
                    "description": "Q4: Years investing"
                },
                "past_behavior": {
                    "type": "string",
                    "enum": ["held", "sold_some", "sold_all", "unknown"],
                    "description": "Q5: Did they hold or sell during past crash?"
                },
                "income_stability": {
                    "type": "string",
                    "enum": ["very_stable", "stable", "moderate", "unstable"],
                    "description": "Q6: How stable is employment/income?"
                },
                "emergency_fund": {
                    "type": "boolean",
                    "description": "Q7: Do they have 6+ months emergency fund?"
                },
                "goal_preference": {
                    "type": "string",
                    "enum": ["income", "growth", "balanced", "unknown"],
                    "description": "Q8: Are they seeking income or growth?"
                }
            }
        },
        "risk_scores_so_far": {
            "type": "object",
            "description": "Scores for each question answered",
            "properties": {
                "question_number": {"type": "integer"},
                "score": {"type": "integer", "minimum": 1, "maximum": 10}
            }
        },
        "assessment_progress": {
            "type": "object",
            "description": "Overall assessment progress",
            "properties": {
                "questions_answered": {"type": "integer", "minimum": 0, "maximum": 8},
                "is_complete": {"type": "boolean", "description": "True if all 8 answered"},
                "preliminary_risk_score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Weighted average risk score so far"
                },
                "preliminary_classification": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive"],
                    "description": "Risk classification based on answers so far"
                }
            }
        },
        "response_to_user": {
            "type": "string",
            "description": "Natural conversational response acknowledging their answer and asking next question"
        }
    },
    "required": ["next_question", "question_number", "response_to_user", "assessment_progress"]
}

# Initial greeting for risk assessment
RISK_ASSESSMENT_GREETING = """Great! Now let's do a quick risk assessment to make sure we create a portfolio that matches your comfort level with investment volatility.

This should take about 10 minutes. I'll ask you 8 questions about your investment experience, comfort with market ups and downs, and your financial situation. Your answers will help me determine if you should be investing conservatively, moderately, or aggressively.

Let's get started. First: We know you're investing for {horizon} years. Now, thinking about that timeframe, how would you describe your comfort level with investment volatility—the natural ups and downs of the market? Are you generally:
- **Conservative** (prefer steady, predictable returns even if lower)
- **Moderate** (okay with some ups and downs as long as long-term trend is up)
- **Aggressive** (comfortable with significant swings for higher potential returns)"""

# Questions for each phase of assessment
RISK_QUESTIONS = {
    1: """We know your investment horizon is {horizon} years. That's a good timeframe. 

Now let's think about volatility. If your portfolio went up 10% one year but then down 8% the next year, would that:
- Make you nervous and want to sell? (Conservative)
- Seem normal and not bother you? (Aggressive)
- Be okay as long as the overall trend is up? (Moderate)""",
    
    2: """Let's imagine a bigger drop. If your entire investment portfolio suddenly dropped 20% in value, what would you most likely do?
- Panic and sell most of it (Conservative)
- Sell some to reduce losses (Moderate)
- Stay invested and even buy more if prices are down (Aggressive)
- It depends on what caused the drop""",
    
    3: """How long have you been actively investing in stocks, bonds, or funds?
- Less than 2 years
- 2-5 years
- 5-10 years
- 10+ years""",
    
    4: """Going back to major market downturns you may have experienced—like 2008 or 2020—what did you actually do?
- I wasn't investing back then / Not sure
- I sold some investments to reduce losses
- I sold most/all of my investments (panic sold)
- I held everything and didn't panic
- I actually bought more during the downturn (very aggressive)""",
    
    5: """How would you describe your employment and income situation?
- Very stable (secure job, predictable income)
- Stable (good job security, regular income)
- Moderate (some income variability or job change risk)
- Unstable (freelance, commission-based, or uncertain employment)""",
    
    6: """Do you have an emergency fund with 6+ months of living expenses set aside?
- Yes, I'm fully covered
- I have 3-6 months set aside
- I have 1-3 months set aside
- I don't have a formal emergency fund yet""",
    
    7: """When you think about your investment goals, which matters more to you?
- Current income (I want my investments to generate cash flow now)
- Long-term growth (I want my investments to grow in value over time)
- Balanced (equally important)
- I'm not sure""",
    
    8: """Finally, what would concern you most about an investment portfolio?
- Losing money (capital preservation)
- Not growing fast enough (missing out on gains)
- Too much complexity or work managing it
- Environmental/social impact of investments"""
}

# Score mapping for each response type
SCORE_MAPPINGS = {
    "volatility_comfort": {
        "conservative": 2,
        "moderate": 5,
        "aggressive": 8
    },
    "loss_tolerance": {
        20: 2,
        30: 3,
        40: 5,
        50: 8
    },
    "experience": {
        0: 2,
        2: 3,
        5: 5,
        10: 7
    },
    "past_behavior": {
        "panic_sold": 1,
        "sold_some": 4,
        "held": 7,
        "bought_more": 9
    },
    "income_stability": {
        "unstable": 2,
        "moderate": 4,
        "stable": 6,
        "very_stable": 8
    },
    "emergency_fund": {
        False: 2,
        True: 6
    },
    "goal": {
        "income": 3,
        "balanced": 5,
        "growth": 8
    },
    "concern": {
        "loss": 2,
        "growth": 8,
        "complexity": 5,
        "impact": 5
    }
}

ASSESSMENT_COMPLETE_MESSAGE = """Perfect! I've asked all 8 risk questions. Based on your answers, here's what I've determined about your risk profile:

**Your Risk Assessment:**
- Overall Risk Score: {risk_score}/100
- Risk Classification: **{risk_classification}**
- Assessment Confidence: {confidence}%

**What this means:**
{classification_explanation}

This profile will guide how we allocate your portfolio. We'll now move on to detailed portfolio analysis and recommendations based on this profile and your investment goals.

Ready to see your personalized recommendations?"""

CLASSIFICATION_EXPLANATIONS = {
    "conservative": """ - You prefer capital preservation with modest growth
 - Recommended allocation: 20-30% stocks, 70-80% bonds/cash
 - Expected returns: 3-4% annually
 - Expected volatility: ±3-5% in bad years""",
    
    "moderate": """ - You seek balanced growth with manageable volatility
 - Recommended allocation: 50-60% stocks, 40-50% bonds/alternatives  
 - Expected returns: 5-6% annually
 - Expected volatility: ±8-12% in bad years""",
    
    "aggressive": """ - You're focused on maximum long-term growth
 - Recommended allocation: 80-90% stocks, 10-20% alternatives
 - Expected returns: 7-8% annually
 - Expected volatility: ±15-20% in bad years"""
}
