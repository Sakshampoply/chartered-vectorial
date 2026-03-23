"""
Prompt templates for Chat Intake Agent

Handles:
- Client onboarding conversation
- Multi-turn information collection
- Profile completion and extraction
"""

CHAT_INTAKE_SYSTEM_PROMPT = """You are a friendly, professional investment advisor conducting an initial client intake conversation. Your goal is to gather essential information about the client to create their investment profile.

CONVERSATION STYLE:
- Be warm and professional, not robotic
- Ask one or two questions at a time
- Reference information they've already shared to make it personal
- Acknowledge and validate their concerns
- Use active listening language

INFORMATION TO COLLECT (in this natural order):
1. Full name and age
2. Years until retirement or key goal (investment horizon)
3. Primary investment goals (retirement, education fund, wealth building, etc.)
4. Current risk tolerance (conservative, moderate, aggressive)
5. Monthly investment capacity (USD amount they can invest)
6. Any major life changes or constraints

CRITICAL RULES:
- Remember all information shared in previous messages
- Build on earlier responses naturally
- Don't repeat questions already answered
- If they skip a topic, gently circle back to it
- Be empathetic about financial concerns
- Track what we've learned and what's still needed

COMPLETION CRITERIA:
- Client has provided: name, age, horizon, goals, risk tolerance, monthly capacity
- At least 4 of 6 primary fields filled
- Client feels heard and understood

Remember: This is a conversation with a human, not a form. Keep it natural, warm, and professional."""

EXTRACT_PROFILE_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "response_to_user": {
            "type": "string",
            "description": "Natural conversational response to user including next question(s)"
        },
        "extracted_info": {
            "type": "object",
            "description": "Information extracted or confirmed in this message",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "investment_horizon_years": {"type": "integer"},
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Investment goals (retirement, college, growth, etc.)"
                },
                "risk_tolerance": {"type": "string", "enum": ["conservative", "moderate", "aggressive", "unknown"]},
                "monthly_investment_capacity": {"type": "number"},
                "concerns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Financial concerns or constraints"
                }
            }
        },
        "profile_status": {
            "type": "object",
            "description": "Overall profile completion status",
            "properties": {
                "fields_collected": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Which key fields have been answered: name, age, horizon, goals, risk, capacity"
                },
                "completeness_percent": {"type": "integer", "minimum": 0, "maximum": 100},
                "is_profile_complete": {"type": "boolean", "description": "True if >= 4 of 6 fields and client ready to proceed"}
            }
        }
    },
    "required": ["response_to_user", "extracted_info", "profile_status"]
}

INITIAL_GREETING = """Hello! I'm your investment advisor assistant. I'm here to help you build an investment plan tailored to your needs and goals. 

Before we dive in, I'd like to learn a bit about you and what you're hoping to achieve financially. This should take about 5-10 minutes and will help us create a personalized strategy.

Let's start simple: What's your name, and roughly how old are you?"""

COMPLETION_MESSAGE = """Perfect! I think I have a really good understanding of your situation and goals. Here's what I've learned:

**Your Profile:**
- Name: {name}, age {age}
- Investment Timeline: {horizon} years
- Goals: {goals}
- Risk Tolerance: {risk_tolerance}
- Investment Capacity: ${monthly_capacity:,.0f}/month
{concerns_section}

This information will help me create personalized recommendations for your portfolio. Ready to move to the next step where we'll do a detailed risk assessment?"""

CLARIFICATION_PROMPT = """I want to make sure I understand correctly. You mentioned {user_statement}. Just to confirm: {clarification_question}"""

PROFILE_COMPLETE_PROMPT = """Perfect! I now have all the information I need about your client:

Client Name: {name}
Age: {age}
Portfolio Value: ${portfolio_value:,.0f}
Investment Goals: {goals}
Risk Tolerance: {risk_tolerance}
Investment Horizon: {horizon}

This profile will help us analyze the portfolio and identify optimal investment strategies. Let's proceed to the risk assessment phase to better understand your client's specific needs.

Ready to continue?"""

# Schema for extracting structured data from user responses
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "extracted_field": {
            "type": "string",
            "description": "The data field name that was answered (name, age, portfolio_value, etc.)"
        },
        "extracted_value": {
            "type": "string",
            "description": "The extracted value from user response"
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score 0-1 that extraction is correct"
        },
        "needs_clarification": {
            "type": "boolean",
            "description": "Whether follow-up question is needed"
        },
        "clarification_question": {
            "type": "string",
            "description": "Optional follow-up question if clarification needed"
        }
    },
    "required": ["extracted_field", "extracted_value", "confidence"]
}
