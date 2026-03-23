"""
Risk & Goals Assessment Agent (Stage 2)

Extended questioning approach (7 questions):
- Questions 1-2 (EXISTING): Risk tolerance + household income
- Questions 3-7 (NEW): Cash on hand, monthly income, tax status, investment horizon, liquidity needs
- Question 8 (OPTIONAL): Primary goal

Replaces the previous ChatIntakeAgent (5-7 questions) + RiskProfilerAgent (8 questions)
"""

import logging
from typing import Dict, Any, Tuple, Optional
import json
from app.services.llm_wrapper import LLMWrapper
from app.agents.prompts.risk_goals_assessment import (
    RISK_GOALS_SYSTEM_PROMPT,
    RISK_GOALS_QUESTION_1,
    RISK_GOALS_QUESTION_2,
    RISK_GOALS_QUESTION_3,
    EXTRACT_RISK_GOALS_SCHEMA,
    COMPLETION_MESSAGE_TEMPLATE,
    SKIP_OPTIONAL_QUESTION,
)
from app.agents.state import AnalysisState

logger = logging.getLogger(__name__)


class RiskGoalsAssessmentAgent:
    """
    Extended questioning agent for Stage 2: Risk & Goals Assessment
    
    Collects 7 required questions:
    1. Risk tolerance level (conservative/moderate/aggressive)
    2. Annual household income
    3. Cash on hand (liquid cash available RIGHT NOW)
    4. Monthly investable income (from salary)
    5. Tax status (single/married/trust)
    6. Investment horizon (months until funds needed)
    7. Liquidity needs (% of portfolio for emergencies)
    
    Plus 1 optional:
    8. Primary investment goal (retirement/growth/income/education)
    """
    
    # Progress tracking: 7 required questions
    PROGRESS_MAPPING = {
        "question_1": 14,   # 1/7
        "question_2": 29,   # 2/7
        "question_3": 43,   # 3/7
        "question_4": 57,   # 4/7
        "question_5": 71,   # 5/7
        "question_6": 86,   # 6/7
        "question_7": 100,  # 7/7
        "complete": 100,
    }
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None):
        """
        Initialize agent
        
        Args:
            llm_wrapper: LLMWrapper instance; creates new if None
        """
        self.llm = llm_wrapper or LLMWrapper(model_name="gpt-oss-120b")
        self.logger = logger
    
    async def get_initial_question(self) -> Tuple[str, Dict[str, Any]]:
        """
        Return the first question (Risk Tolerance)
        
        Returns:
            (question_text, metadata_dict)
        """
        return (
            RISK_GOALS_QUESTION_1,
            {
                "question_type": "risk_tolerance",
                "question_number": 1,
                "is_required": True,
                "progress": self.PROGRESS_MAPPING["question_1"],
            },
        )
    
    async def process_response(
        self,
        state: AnalysisState,
        user_response: str,
        question_type: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process user response and determine next question or completion
        
        Args:
            state: Current analysis state
            user_response: User's answer to current question
            question_type: Which question this is answering 
                (risk_tolerance | household_income | cash_on_hand | monthly_income | 
                 tax_status | investment_horizon | liquidity_needs | primary_goal)
            
        Returns:
            (next_prompt_or_confirmation, extraction_result_dict)
        """
        try:
            extracted = {}
            completion = {
                "q1_risk_tolerance": bool(state.get("risk_profile")),
                "q2_household_income": state.get("household_income") is not None,
                "q3_cash_on_hand": state.get("cash_on_hand") is not None,
                "q4_monthly_income": state.get("monthly_investable_income") is not None,
                "q5_tax_status": state.get("tax_status") is not None,
                "q6_investment_horizon": state.get("investment_horizon_months") is not None,
                "q7_liquidity_needs": state.get("liquidity_needs_pct") is not None,
                "q8_primary_goal": state.get("primary_goal") is not None,
                "all_required_complete": False,
                "progress_percent": 0,
            }
            
            # Extract based on question type
            if question_type == "risk_tolerance":
                response_lower = user_response.lower()
                
                if any(word in response_lower for word in ["moderate", "balanced", "balance", "medium"]):
                    extracted["risk_tolerance"] = "moderate"
                    state["risk_profile"] = "moderate"
                elif any(word in response_lower for word in ["conservative", "preserve", "stable", "low", "capital preservation"]):
                    extracted["risk_tolerance"] = "conservative"
                    state["risk_profile"] = "conservative"
                elif any(word in response_lower for word in ["aggressive", "growth", "high", "volatility", "maximize"]):
                    extracted["risk_tolerance"] = "aggressive"
                    state["risk_profile"] = "aggressive"
                else:
                    return ("I didn't quite understand that. Please choose: conservative, moderate, or aggressive.", {
                        "status": "invalid",
                        "error": "Invalid risk tolerance response",
                    })
                
                self.logger.info(f"Q1 - Risk tolerance: {extracted['risk_tolerance']}")
            
            elif question_type == "household_income":
                import re
                response_lower = user_response.lower()
                numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([km]?)', response_lower.replace(',', ''))
                
                income = None
                if numbers:
                    num_str, multiplier = numbers[0]
                    num = float(num_str)
                    if multiplier == 'k':
                        income = num * 1000
                    elif multiplier == 'm':
                        income = num * 1000000
                    else:
                        if num < 500:
                            income = num * 1000
                        else:
                            income = num
                
                if income and income > 0:
                    state["household_income"] = income
                    extracted["household_income"] = income
                    self.logger.info(f"Q2 - Household income: ${income:,.0f}")
                else:
                    return ("Please enter a valid income amount (e.g., $50,000 or 50k).", {
                        "status": "invalid",
                        "error": "Invalid income format",
                    })
            
            elif question_type == "cash_on_hand":
                # Q3: Cash available right now
                import re
                response_lower = user_response.lower()
                
                # Handle "zero", "$0", "none", etc.
                if any(word in response_lower for word in ["zero", "none", "$0", "no cash", "nothing", "fully invested"]):
                    cash = 0.0
                else:
                    numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([km]?)', response_lower.replace(',', ''))
                    if numbers:
                        num_str, multiplier = numbers[0]
                        num = float(num_str)
                        if multiplier == 'k':
                            cash = num * 1000
                        elif multiplier == 'm':
                            cash = num * 1000000
                        else:
                            cash = num
                    else:
                        return ("Please enter a cash amount (e.g., $5,000 or 5k, or 'none' if $0).", {
                            "status": "invalid",
                            "error": "Invalid cash amount",
                        })
                
                state["cash_on_hand"] = max(0, cash)
                extracted["cash_on_hand"] = state["cash_on_hand"]
                self.logger.info(f"Q3 - Cash on hand: ${state['cash_on_hand']:,.0f}")
            
            elif question_type == "monthly_investable_income":
                # Q4: Monthly amount from salary
                import re
                response_lower = user_response.lower()
                
                if any(word in response_lower for word in ["zero", "none", "$0", "no", "nothing"]):
                    monthly_income = 0.0
                else:
                    numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([km]?)', response_lower.replace(',', ''))
                    if numbers:
                        num_str, multiplier = numbers[0]
                        num = float(num_str)
                        if multiplier == 'k':
                            monthly_income = num * 1000
                        elif multiplier == 'm':
                            monthly_income = num * 1000000
                        else:
                            monthly_income = num
                    else:
                        return ("Please enter a monthly amount (e.g., $500 or 500, or 'none' if $0).", {
                            "status": "invalid",
                            "error": "Invalid monthly income",
                        })
                
                state["monthly_investable_income"] = max(0, monthly_income)
                extracted["monthly_investable_income"] = state["monthly_investable_income"]
                self.logger.info(f"Q4 - Monthly investable income: ${state['monthly_investable_income']:,.0f}")
            
            elif question_type == "tax_status":
                # Q5: Tax filing status
                response_lower = user_response.lower()
                
                if any(word in response_lower for word in ["single", "unmarried", "1"]):
                    tax_status = "single"
                elif any(word in response_lower for word in ["married", "joint", "2", "mfj"]):
                    tax_status = "married"
                elif any(word in response_lower for word in ["trust", "corp", "business", "entity"]):
                    tax_status = "trust"
                else:
                    return ("Please choose: single, married, or trust.", {
                        "status": "invalid",
                        "error": "Invalid tax status",
                    })
                
                state["tax_status"] = tax_status
                extracted["tax_status"] = tax_status
                self.logger.info(f"Q5 - Tax status: {tax_status}")
            
            elif question_type == "investment_horizon":
                # Q6: Investment horizon in months
                import re
                response_lower = user_response.lower()
                
                # Check for keywords
                if any(word in response_lower for word in ["1-3 year", "short", "1-3y"]):
                    months = 24  # midpoint of 12-36
                elif any(word in response_lower for word in ["3-5 year", "medium", "3-5y"]):
                    months = 48  # midpoint of 36-60
                elif any(word in response_lower for word in ["5-10 year", "long", "5-10y"]):
                    months = 84  # midpoint of 60-120
                elif any(word in response_lower for word in ["10+ year", "very long", "10+y", "retirement", "indefinite"]):
                    months = 180  # 15 years as proxy
                else:
                    # Try to extract number
                    numbers = re.findall(r'(\d+)', response_lower)
                    if numbers:
                        months = int(numbers[0])
                        if months < 12:
                            months = months * 12  # Assume years if single digit
                    else:
                        return ("Please enter a timeline (e.g., '5 years', '3-5 years', or '60 months').", {
                            "status": "invalid",
                            "error": "Invalid investment horizon",
                        })
                
                if months <= 0:
                    return ("Investment horizon must be positive. Please try again.", {
                        "status": "invalid",
                        "error": "Invalid horizon (<=0)",
                    })
                
                state["investment_horizon_months"] = months
                extracted["investment_horizon_months"] = months
                self.logger.info(f"Q6 - Investment horizon: {months} months")
            
            elif question_type == "liquidity_needs":
                # Q7: Liquidity needs as % of portfolio
                import re
                response_lower = user_response.lower()
                
                # Try to extract percentage
                pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%?', response_lower)
                if pct_match:
                    liquidity_pct = float(pct_match.group(1))
                    if not response_lower.endswith('%') and liquidity_pct > 1:
                        # If no % sign and number > 1, it's already a percentage
                        pass
                    elif response_lower.endswith('%') or '%' in response_lower:
                        # Already a percentage
                        pass
                    elif liquidity_pct < 1:
                        # Decimal like 0.1 → 10%
                        liquidity_pct = liquidity_pct * 100
                else:
                    return ("Please enter a percentage (e.g., 10%, 25%, or '0' if none).", {
                        "status": "invalid",
                        "error": "Invalid liquidity percentage",
                    })
                
                liquidity_pct = max(0, min(100, liquidity_pct))  # Clamp to 0-100
                state["liquidity_needs_pct"] = liquidity_pct
                extracted["liquidity_needs_pct"] = liquidity_pct
                self.logger.info(f"Q7 - Liquidity needs: {liquidity_pct}%")
            
            elif question_type == "primary_goal":
                # Q8: Primary goal (optional after Q7)
                response_lower = user_response.lower()
                
                if any(word in response_lower for word in ["retire", "retirement"]):
                    extracted["primary_goal"] = "retirement"
                    state["primary_goal"] = "retirement"
                elif any(word in response_lower for word in ["grow", "wealth", "growth"]):
                    extracted["primary_goal"] = "growth"
                    state["primary_goal"] = "growth"
                elif any(word in response_lower for word in ["income", "dividend", "cash flow"]):
                    extracted["primary_goal"] = "income"
                    state["primary_goal"] = "income"
                elif any(word in response_lower for word in ["education", "college", "tuition"]):
                    extracted["primary_goal"] = "education"
                    state["primary_goal"] = "education"
                else:
                    extracted["primary_goal"] = "other"
                
                self.logger.info(f"Q8 - Primary goal: {extracted.get('primary_goal')}")
            
            # Update completion tracking
            completion["q1_risk_tolerance"] = state.get("risk_profile") is not None
            completion["q2_household_income"] = state.get("household_income") is not None
            completion["q3_cash_on_hand"] = state.get("cash_on_hand") is not None
            completion["q4_monthly_income"] = state.get("monthly_investable_income") is not None
            completion["q5_tax_status"] = state.get("tax_status") is not None
            completion["q6_investment_horizon"] = state.get("investment_horizon_months") is not None
            completion["q7_liquidity_needs"] = state.get("liquidity_needs_pct") is not None
            completion["q8_primary_goal"] = state.get("primary_goal") is not None
            
            # All 7 required questions answered?
            all_required = all([
                completion["q1_risk_tolerance"],
                completion["q2_household_income"],
                completion["q3_cash_on_hand"],
                completion["q4_monthly_income"],
                completion["q5_tax_status"],
                completion["q6_investment_horizon"],
                completion["q7_liquidity_needs"],
            ])
            
            completion["all_required_complete"] = all_required
            
            if all_required:
                completion["progress_percent"] = 100
                state["info_collection_complete"] = True
                state["info_collection_progress"] = 1.0
                
                # Calculate implementation scenario
                self._calculate_implementation_scenario(state)
                
                next_prompt = (
                    f"✓ Perfect! I have all the information I need:\n"
                    f"- Risk Profile: {state.get('risk_profile')}\n"
                    f"- Household Income: ${state.get('household_income', 0):,.0f}/year\n"
                    f"- Cash on Hand: ${state.get('cash_on_hand', 0):,.0f}\n"
                    f"- Monthly Investment Capacity: ${state.get('monthly_investable_income', 0):,.0f}\n"
                    f"- Tax Status: {state.get('tax_status')}\n"
                    f"- Time Horizon: {state.get('investment_horizon_months')} months\n"
                    f"- Liquidity Needs: {state.get('liquidity_needs_pct', 0)}% of portfolio\n"
                    f"\nStarting portfolio analysis..."
                )
            else:
                # Calculate progress based on answered questions
                answered = sum([
                    completion["q1_risk_tolerance"],
                    completion["q2_household_income"],
                    completion["q3_cash_on_hand"],
                    completion["q4_monthly_income"],
                    completion["q5_tax_status"],
                    completion["q6_investment_horizon"],
                    completion["q7_liquidity_needs"],
                ])
                completion["progress_percent"] = int((answered / 7) * 100)
                state["info_collection_progress"] = completion["progress_percent"] / 100.0
                next_prompt = "Thank you for that information."
            
            return (
                next_prompt,
                {
                    "status": "success",
                    "extracted_info": extracted,
                    "completion_status": completion,
                    "updated_state": {
                        "risk_profile": state.get("risk_profile"),
                        "household_income": state.get("household_income"),
                        "cash_on_hand": state.get("cash_on_hand"),
                        "monthly_investable_income": state.get("monthly_investable_income"),
                        "tax_status": state.get("tax_status"),
                        "investment_horizon_months": state.get("investment_horizon_months"),
                        "liquidity_needs_pct": state.get("liquidity_needs_pct"),
                        "primary_goal": state.get("primary_goal"),
                        "implementation_scenario": state.get("implementation_scenario"),
                        "info_collection_complete": state.get("info_collection_complete"),
                        "info_collection_progress": state.get("info_collection_progress"),
                    },
                },
            )
        
        except Exception as e:
            self.logger.error(f"Error processing response: {str(e)}", exc_info=True)
            return (
                "I had trouble processing that response. Could you try again?",
                {
                    "status": "error",
                    "error": str(e),
                    "extracted_info": {},
                    "completion_status": {
                        "all_required_complete": False,
                        "progress_percent": state.get("info_collection_progress", 0) * 100,
                    },
                },
            )
    
    def skip_optional_question(self, state: AnalysisState) -> Tuple[str, Dict[str, Any]]:
        """
        Skip the optional goal question and proceed to analysis
        
        Args:
            state: Current analysis state
            
        Returns:
            (completion_prompt, metadata)
        """
        state["info_collection_complete"] = True
        state["info_collection_progress"] = 1.0
        
        prompt = SKIP_OPTIONAL_QUESTION.format(
            risk_tolerance=state.get("risk_profile", "unknown"),
            household_income=state.get("household_income", 0),
        )
        
        return (
            prompt,
            {
                "status": "skipped_optional",
                "message": "Skipped optional goal question, ready for analysis",
                "info_collection_complete": True,
            },
        )
    
    def _state_summary(self, state: AnalysisState) -> Dict[str, Any]:
        """Create a JSON-serializable summary of state for LLM context"""
        return {
            "risk_profile": state.get("risk_profile"),
            "household_income": state.get("household_income"),
            "cash_on_hand": state.get("cash_on_hand"),
            "monthly_investable_income": state.get("monthly_investable_income"),
            "tax_status": state.get("tax_status"),
            "investment_horizon_months": state.get("investment_horizon_months"),
            "liquidity_needs_pct": state.get("liquidity_needs_pct"),
            "primary_goal": state.get("primary_goal"),
            "info_collection_progress": state.get("info_collection_progress"),
        }
    
    def _calculate_implementation_scenario(self, state: AnalysisState) -> None:
        """
        Calculate implementation scenario based on cash availability and monthly income
        
        Sets state["implementation_scenario"] to one of:
        - "immediate": Have enough cash to rebalance now
        - "phased_6m": Fund from monthly income over 6 months
        - "phased_12m": Fund from monthly income over 12 months
        - "requires_liquidation": No cash or income; must sell existing positions
        
        Note: This is a placeholder; the actual scenario will be recalculated  
        in InvestmentRecommendationAgent once trade costs are known.
        """
        cash = state.get("cash_on_hand", 0) or 0
        monthly = state.get("monthly_investable_income", 0) or 0
        
        if cash > 0 and cash > 10000:  # Rough threshold for "enough" cash
            state["implementation_scenario"] = "immediate"
        elif monthly > 0:
            # Estimate funding need at ~$20k (typical rebalancing cost)
            estimated_cost = 20000
            months_needed = estimated_cost / monthly
            
            if months_needed <= 6:
                state["implementation_scenario"] = "phased_6m"
            elif months_needed <= 12:
                state["implementation_scenario"] = "phased_12m"
            else:
                state["implementation_scenario"] = "requires_liquidation"
        else:
            state["implementation_scenario"] = "requires_liquidation"
        
        self.logger.info(f"Calculated implementation scenario: {state['implementation_scenario']}")
