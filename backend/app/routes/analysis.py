"""
API routes for 3-stage analysis workflow

Endpoints:
POST   /api/analysis/start          - Create new analysis (Stage 1 init)
POST   /api/analysis/{id}/info      - Collect 2-3 questions (Stage 2)
POST   /api/analysis/{id}/execute   - Run 3 agents in parallel (Stage 3)
GET    /api/analysis/{id}/progress  - Get execution progress
GET    /api/analysis/{id}/results   - Get final analysis results
POST   /api/analysis/{id}/ask       - Cross-questioning with metrics
GET    /api/analysis/{id}           - Get analysis status
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID
import logging
from datetime import datetime
import asyncio
import json

from app.database import get_db
from app.agents import AnalysisState, AnalysisStage, AnalysisStateFactory
from app.agents.risk_goals_assessment import RiskGoalsAssessmentAgent
from app.agents.portfolio_analysis_agent import PortfolioAnalysisAgent
from app.agents.risk_assessment_agent import RiskAssessmentAgent
from app.agents.investment_recommendation_agent import InvestmentRecommendationAgent
from app.agents.metrics_interpreter_agent import MetricsInterpreterAgent
from app.agents.recommendation_rationale_agent import RecommendationRationaleAgent
from app.models.client import AnalysisResult, Portfolio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# In-memory storage (replace with database in production)
ANALYSIS_STORE: Dict[str, AnalysisState] = {}


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/start")
async def start_analysis(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Initialize new analysis (Stage 1 completion)
    
    Called after document upload succeeds. Sets up the analysis workflow.
    
    Request body (format after portfolio upload):
    {
        "client_id": "client_uuid_string",
        "portfolio_id": "portfolio_uuid_from_upload_response"
    }
    
    OR if only portfolio_id is provided:
    {
        "portfolio_id": "portfolio_uuid_from_upload_response"
    }
    
    Returns: analysis_id and ready for Stage 2 (info collection)
    """
    try:
        client_id = request.get("client_id")
        portfolio_id = request.get("portfolio_id")
        
        # If only portfolio_id provided, fetch client from database
        if portfolio_id and not client_id:
            from app.models.client import Portfolio
            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise HTTPException(
                    status_code=404,
                    detail=f"Portfolio {portfolio_id} not found. Make sure the upload was successful."
                )
            client_id = str(portfolio.client_id)
            logger.info(f"Resolved client_id {client_id} from portfolio {portfolio_id}")
        
        # Validate both are present
        if not client_id or not portfolio_id:
            raise HTTPException(
                status_code=400,
                detail="Either (client_id, portfolio_id) or just portfolio_id required. "
                       "Make sure portfolio upload was successful and returned portfolio_id."
            )
        
        # Verify portfolio exists and belongs to client
        from app.models.client import Portfolio
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.client_id == client_id
        ).first()
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail=f"Portfolio {portfolio_id} not found for client {client_id}. "
                       f"Ensure you're using the correct client_id that uploaded the portfolio."
            )
        
        # Create new analysis linked to portfolio using proper UUID
        analysis_uuid = uuid4()
        analysis_id = str(analysis_uuid)
        state = AnalysisStateFactory.create_new(analysis_id, str(client_id))
        state["portfolio_id"] = str(portfolio_id)
        state["stage"] = AnalysisStage.INFO_COLLECTION  # Move to Stage 2
        
        # Store in memory with UUID (matches database schema)
        ANALYSIS_STORE[analysis_id] = state
        
        logger.info(
            f"Started analysis {analysis_id} for client {client_id}, "
            f"portfolio {portfolio_id}"
        )
        
        return {
            "analysis_id": analysis_id,
            "status": "ready",
            "stage": AnalysisStage.INFO_COLLECTION,
            "next_step": "collect_info",
            "created_at": state["created_at"],
            "portfolio_id": str(portfolio_id),
            "client_id": str(client_id)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STAGE 2: INFO COLLECTION (2-3 Questions)
# ============================================================================

@router.post("/{analysis_id}/info")
async def collect_risk_goals_info(
    analysis_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Stage 2: Collect intake data via 7 required + 1 optional question sequence
    
    Sequential flow (7 required questions):
    1. Risk Tolerance - conservative/moderate/aggressive
    2. Household Income - annual USD amount
    3. Cash on Hand - liquid USD available
    4. Monthly Investable Income - after expenses USD
    5. Tax Status - single/married/business/etc
    6. Investment Horizon - months until needed
    7. Liquidity Needs - % of portfolio needed annually
    8. Primary Goal (optional) - retirement/growth/income/education
    
    After all 7 required answered → transitions to Stage 3 execution
    Optional Q8 can be skipped
    
    Request body (first call, no answer):
    {}
    
    Request body (with answer):
    {"answer": "moderate"}
    
    Returns: current question, progress percent 14-100%, transitions to PORTFOLIO_ANALYSIS when done
    """
    try:
        if analysis_id not in ANALYSIS_STORE:
            # Check database if not in memory (analysis was completed/persisted earlier)
            analysis_record = db.query(AnalysisResult).filter(
                AnalysisResult.id == UUID(analysis_id)
            ).first()
            
            if analysis_record:
                raise HTTPException(
                    status_code=400,
                    detail=f"Info collection already complete for this analysis. Use /results to view analysis."
                )
            
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        state = ANALYSIS_STORE[analysis_id]
        
        if state["stage"] != AnalysisStage.INFO_COLLECTION:
            raise HTTPException(
                status_code=400,
                detail=f"Info collection not available in stage {state['stage']}"
            )
        
        agent = RiskGoalsAssessmentAgent()
        answer = request.get("answer", "").strip()
        
        # Define the 8-question sequence: 7 required + 1 optional
        REQUIRED_QUESTIONS = [
            "risk_tolerance",
            "household_income",
            "cash_on_hand",
            "monthly_investable_income",
            "tax_status",
            "investment_horizon",
            "liquidity_needs",
        ]
        OPTIONAL_QUESTIONS = ["primary_goal"]
        ALL_QUESTIONS = REQUIRED_QUESTIONS + OPTIONAL_QUESTIONS
        
        # Question metadata
        QUESTION_METADATA = {
            "risk_tolerance": {
                "order": 1,
                "text": "What is your risk tolerance: conservative, moderate, or aggressive?",
                "help": "This helps us understand how much portfolio volatility you can tolerate",
                "is_required": True
            },
            "household_income": {
                "order": 2,
                "text": "What is your annual household income (in USD)?",
                "help": "This helps us understand your overall financial capacity",
                "is_required": True
            },
            "cash_on_hand": {
                "order": 3,
                "text": "How much liquid cash do you have available (in USD)?",
                "help": "This is the amount you can immediately invest",
                "is_required": True
            },
            "monthly_investable_income": {
                "order": 4,
                "text": "How much can you invest monthly after expenses (in USD)?",
                "help": "This is your ongoing investment capacity",
                "is_required": True
            },
            "tax_status": {
                "order": 5,
                "text": "What is your tax status? (e.g., single, married, s-corp, c-corp)",
                "help": "Tax-efficient strategies depend on your filing status",
                "is_required": True
            },
            "investment_horizon": {
                "order": 6,
                "text": "What is your investment timeline in months?",
                "help": "Longer horizons allow for more growth-oriented strategies",
                "is_required": True
            },
            "liquidity_needs": {
                "order": 7,
                "text": "What percentage of your portfolio do you need as liquidity annually? (0-100)",
                "help": "This helps us preserve funds for your regular withdrawals",
                "is_required": True
            },
            "primary_goal": {
                "order": 8,
                "text": "What is your primary investment goal? (Optional: retirement, growth, income, education)",
                "help": "This helps us tailor the investment strategy",
                "is_required": False
            },
        }
        
        # Initialize tracking on first call
        if "answered_questions" not in state:
            state["answered_questions"] = {}  # {question_type: answer_text}
        
        if answer:
            # User is answering a question
            if "pending_question" not in state:
                raise HTTPException(
                    status_code=400,
                    detail="No question pending. Call endpoint without answer first."
                )
            
            current_question_type = state["pending_question"]
            
            # Process the answer through the agent
            next_prompt, result = await agent.process_response(
                state=state,
                user_response=answer,
                question_type=current_question_type
            )
            
            # Store the answer
            state["answered_questions"][current_question_type] = answer
            
            # Get completion status from agent
            completion_status = result.get("completion_status", {})
            all_required_complete = completion_status.get("all_required_complete", False)
            progress_percent = completion_status.get("progress_percent", 0)
            
            # Case 1: All 7 required questions answered - transition to Stage 3
            if all_required_complete:
                state["info_collection_complete"] = True
                state["stage"] = AnalysisStage.PORTFOLIO_ANALYSIS
                state.pop("pending_question", None)  # Clear pending question
                
                logger.info(
                    f"Info collection COMPLETE for {analysis_id}: "
                    f"7 required questions answered, transitioning to Stage 3 execution"
                )
                
                return {
                    "analysis_id": analysis_id,
                    "status": "complete",
                    "progress": 1.0,
                    "message": next_prompt,
                    "stage": "PORTFOLIO_ANALYSIS",
                    "collected": {
                        "risk_profile": state.get("risk_profile"),
                        "household_income": state.get("household_income"),
                        "cash_on_hand": state.get("cash_on_hand"),
                        "monthly_investable_income": state.get("monthly_investable_income"),
                        "tax_status": state.get("tax_status"),
                        "investment_horizon_months": state.get("investment_horizon_months"),
                        "liquidity_needs_pct": state.get("liquidity_needs_pct"),
                        "implementation_scenario": state.get("implementation_scenario"),
                    }
                }
            
            # Case 2: Still need more required questions - find next one
            next_question = None
            for q_type in REQUIRED_QUESTIONS:
                if q_type not in state["answered_questions"]:
                    next_question = q_type
                    break
            
            # Case 3: All required done, ask optional
            if next_question is None and "primary_goal" not in state["answered_questions"]:
                next_question = "primary_goal"
            
            # Case 4: All questions done
            if next_question is None:
                state["info_collection_complete"] = True
                state["stage"] = AnalysisStage.PORTFOLIO_ANALYSIS
                state.pop("pending_question", None)
                
                return {
                    "analysis_id": analysis_id,
                    "status": "complete",
                    "progress": 1.0,
                    "message": "All questions answered. Ready to begin analysis.",
                    "stage": "PORTFOLIO_ANALYSIS",
                    "collected": result.get("updated_state", {})
                }
            
            # Set pending question and return it
            state["pending_question"] = next_question
            q_meta = QUESTION_METADATA[next_question]
            
            return {
                "analysis_id": analysis_id,
                "status": "in_progress",
                "progress": progress_percent / 100.0 if progress_percent > 0 else 0.14,  # Begin at 14% after first answer
                "message": next_prompt,
                "question": q_meta["text"],
                "question_type": next_question,
                "question_number": q_meta["order"],
                "is_required": q_meta["is_required"],
                "help_text": q_meta["help"],
                "can_skip": not q_meta["is_required"]
            }
        
        else:
            # No answer provided - return current or next question
            if "pending_question" in state:
                # Client is asking for the pending question again
                q_type = state["pending_question"]
                q_meta = QUESTION_METADATA[q_type]
                
                return {
                    "analysis_id": analysis_id,
                    "status": "in_progress",
                    "progress": 0.14 + (len(state.get("answered_questions", {})) * 0.11),  # Estimated progress
                    "question": q_meta["text"],
                    "question_type": q_type,
                    "question_number": q_meta["order"],
                    "is_required": q_meta["is_required"],
                    "help_text": q_meta["help"],
                    "can_skip": not q_meta["is_required"]
                }
            
            # First call ever - find first unanswered question
            if not state.get("answered_questions"):
                # Start with Q1
                first_q = REQUIRED_QUESTIONS[0]
                state["pending_question"] = first_q
                q_meta = QUESTION_METADATA[first_q]
                
                return {
                    "analysis_id": analysis_id,
                    "status": "in_progress",
                    "progress": 0.0,
                    "question": q_meta["text"],
                    "question_type": first_q,
                    "question_number": q_meta["order"],
                    "is_required": q_meta["is_required"],
                    "help_text": q_meta["help"],
                    "questions_total": 8,
                    "questions_required": 7
                }
            
            # In progress - find next unanswered question
            next_q = None
            for q_type in ALL_QUESTIONS:
                if q_type not in state.get("answered_questions", {}):
                    next_q = q_type
                    break
            
            if next_q:
                state["pending_question"] = next_q
                q_meta = QUESTION_METADATA[next_q]
                
                return {
                    "analysis_id": analysis_id,
                    "status": "in_progress",
                    "progress": 0.14 + (len(state.get("answered_questions", {})) * 0.11),
                    "question": q_meta["text"],
                    "question_type": next_q,
                    "question_number": q_meta["order"],
                    "is_required": q_meta["is_required"],
                    "help_text": q_meta["help"],
                    "can_skip": not q_meta["is_required"]
                }
            
            # All done
            state["info_collection_complete"] = True
            state["stage"] = AnalysisStage.PORTFOLIO_ANALYSIS
            state.pop("pending_question", None)
            
            return {
                "analysis_id": analysis_id,
                "status": "complete",
                "progress": 1.0,
                "message": "All questions answered. Ready to begin analysis.",
                "stage": "PORTFOLIO_ANALYSIS"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ============================================================================
# STAGE 3: EXECUTE ANALYSIS (3 Agents in Sequential Mode)
# ============================================================================

@router.post("/{analysis_id}/execute")
async def execute_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Stage 3: Execute 3 specialized agents sequentially
    
    Agents run in order with progress tracking:
    1. PortfolioAnalysisAgent (25% weight)
    2. RiskAssessmentAgent (25% weight)
    3. InvestmentRecommendationAgent (50% weight)
    
    Then runs interpretation agents to generate summaries.
    
    Returns immediately with execution started status.
    Check /progress endpoint for real-time progress.
    
    Typical execution time: 15-20 seconds
    """
    try:
        if analysis_id not in ANALYSIS_STORE:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        state = ANALYSIS_STORE[analysis_id]
        
        if state["stage"] not in [
            AnalysisStage.PORTFOLIO_ANALYSIS,
            AnalysisStage.RISK_ASSESSMENT,
            AnalysisStage.RECOMMENDATION
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Execution not available in stage {state['stage']}"
            )
        
        if not state.get("info_collection_complete"):
            raise HTTPException(
                status_code=400,
                detail="Must complete info collection first"
            )
        
        # Start execution asynchronously
        asyncio.create_task(_run_analysis_agents(analysis_id, state, db))
        
        logger.info(f"Started execution for analysis {analysis_id}")
        
        return {
            "analysis_id": analysis_id,
            "status": "executing",
            "message": "Analysis workflow started",
            "estimated_duration_seconds": 20,
            "check_progress_at": f"/api/analysis/{analysis_id}/progress"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_analysis_agents(analysis_id: str, state: AnalysisState, db: Session) -> None:
    """Background task: Execute 3 agents sequentially with progress tracking"""
    try:
        # Initialize progress tracking
        state["stage_progress"] = {
            "portfolio": 0.0,
            "risk": 0.0,
            "recommendation": 0.0
        }
        state["stage_status"] = {
            "portfolio": "queued",
            "risk": "queued",
            "recommendation": "queued"
        }
        state["overall_progress"] = 0.0
        
        # ====================================================================
        # AGENT 1: PORTFOLIO ANALYSIS (25% weight)
        # ====================================================================
        logger.info(f"Starting Portfolio Analysis Agent for {analysis_id}")
        state["stage"] = AnalysisStage.PORTFOLIO_ANALYSIS
        state["stage_status"]["portfolio"] = "running"
        
        portfolio_agent = PortfolioAnalysisAgent(db=db)
        portfolio_results = await portfolio_agent.execute(state)
        # Agent already updated state, but also returns metrics for confirmation
        metrics = portfolio_results.get("metrics", {})
        if metrics:
            # Ensure all values are in state since metrics_interpreter needs them
            state["portfolio_value"] = state.get("portfolio_value") or metrics.get("portfolio_value")
        state["portfolio_summary"] = portfolio_results.get("summary", state.get("portfolio_summary"))
        
        state["stage_progress"]["portfolio"] = 1.0
        state["stage_status"]["portfolio"] = "complete"
        state["overall_progress"] = 0.25
        logger.info(f"Portfolio Analysis complete for {analysis_id}")
        
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # ====================================================================
        # AGENT 2: RISK ASSESSMENT (25% weight)
        # ====================================================================
        logger.info(f"Starting Risk Assessment Agent for {analysis_id}")
        state["stage"] = AnalysisStage.RISK_ASSESSMENT
        state["stage_status"]["risk"] = "running"
        
        risk_agent = RiskAssessmentAgent(db=db)
        risk_results = await risk_agent.execute(state)
        # Agent already updated state directly; results dict is for confirmation
        metrics = risk_results.get("metrics", {})
        # Summary is separately returned
        state["risk_summary"] = risk_results.get("summary", state.get("risk_summary"))
        
        state["stage_progress"]["risk"] = 1.0
        state["stage_status"]["risk"] = "complete"
        state["overall_progress"] = 0.50
        logger.info(f"Risk Assessment complete for {analysis_id}")
        
        await asyncio.sleep(0.5)
        
        # ====================================================================
        # AGENT 3: INVESTMENT RECOMMENDATION (50% weight)
        # ====================================================================
        logger.info(f"Starting Investment Recommendation Agent for {analysis_id}")
        state["stage"] = AnalysisStage.RECOMMENDATION
        state["stage_status"]["recommendation"] = "running"
        
        rec_agent = InvestmentRecommendationAgent(db=db)
        rec_results = await rec_agent.execute(state)
        # Agent already updated state directly; just get the summaries from agent result
        state["execution_plan"] = rec_results.get("recommendation_summary", state.get("execution_plan"))
        state["recommendation_summary"] = rec_results.get("summary", state.get("recommendation_summary"))
        
        state["stage_progress"]["recommendation"] = 1.0
        state["stage_status"]["recommendation"] = "complete"
        state["overall_progress"] = 1.0
        logger.info(f"Investment Recommendation complete for {analysis_id}")
        
        await asyncio.sleep(0.5)
        
        # ====================================================================
        # GENERATE SUMMARIES (MetricsInterpreterAgent + RecommendationRationaleAgent)
        # ====================================================================
        logger.info(f"Generating summaries for {analysis_id}")
        
        metrics_interpreter = MetricsInterpreterAgent()
        metrics_summary = await metrics_interpreter.interpret_all_metrics(state)
        state["metrics_summary"] = metrics_summary
        
        rationale_agent = RecommendationRationaleAgent()
        rationale = await rationale_agent.generate_rationale(state)
        state["recommendation_rationale"] = rationale
        
        # ====================================================================
        # COMPLETION
        # ====================================================================
        state["stage"] = AnalysisStage.ANALYSIS_COMPLETE
        state["duration_seconds"] = (datetime.now() - datetime.fromisoformat(state["created_at"])).total_seconds()
        
        # ====================================================================
        # PERSIST RESULTS TO DATABASE
        # ====================================================================
        try:
            # Convert string IDs to UUIDs
            client_id = UUID(state.get("client_id")) if isinstance(state.get("client_id"), str) else state.get("client_id")
            portfolio_id = UUID(state.get("portfolio_id")) if isinstance(state.get("portfolio_id"), str) else state.get("portfolio_id")
            analysis_id_uuid = UUID(analysis_id)  # Use same UUID as in-memory state
            
            # Create AnalysisResult record with matching UUID
            analysis_result = AnalysisResult(
                id=analysis_id_uuid,  # Use the analysis_id from state
                client_id=client_id,
                portfolio_id=portfolio_id,
                
                # Risk & Goals Assessment (Stage 2)
                risk_profile=state.get("risk_profile", "moderate"),
                household_income=state.get("household_income", 0.0),
                primary_goal=state.get("primary_goal"),
                
                # Portfolio Analysis (Agent 1)
                portfolio_metrics_json={
                    "allocation": state.get("allocation"),
                    "portfolio_value": state.get("portfolio_value"),
                    "diversification_score": state.get("diversification_score"),
                    "concentration_risk": state.get("concentration_risk"),
                    "sector_exposure": state.get("sector_exposure"),
                    "asset_class_exposure": state.get("asset_class_exposure"),
                },
                
                # Risk Assessment (Agent 2)
                risk_metrics_json={
                    "sharpe_ratio": state.get("sharpe_ratio"),
                    "sortino_ratio": state.get("sortino_ratio"),
                    "volatility": state.get("volatility"),
                    "beta": state.get("beta"),
                    "max_drawdown": state.get("max_drawdown"),
                    "var_95": state.get("var_95"),
                    "cvar_95": state.get("cvar_95"),
                    "risk_level": state.get("risk_level"),
                },
                
                # Investment Recommendation (Agent 3)
                recommendation_json={
                    "recommended_allocation": state.get("recommended_allocation"),
                    "projected_return": state.get("projected_return"),
                    "projected_volatility": state.get("projected_volatility"),
                    "projected_sharpe": state.get("projected_sharpe"),
                    "rebalancing_trades": state.get("rebalancing_trades"),
                    "implementation_cost": state.get("implementation_cost"),
                    "tax_impact": state.get("tax_impact"),
                    "execution_plan": state.get("execution_plan"),
                },
                
                # LLM Summaries
                metrics_summary_json=state.get("metrics_summary"),
                rationale_json=state.get("recommendation_rationale"),
                
                # Metadata
                duration_seconds=state["duration_seconds"],
                overall_progress=state["overall_progress"],
                status="complete",
                completed_at=datetime.utcnow(),
            )
            
            # Add to database and commit
            db.add(analysis_result)
            db.commit()
            db.refresh(analysis_result)
            
            logger.info(f"Persisted analysis results to database: {analysis_result.id}")
            
        except Exception as db_error:
            logger.warning(f"Failed to persist analysis to database: {str(db_error)}", exc_info=True)
            # Don't fail the analysis if database persistence fails - still keep in-memory copy
            db.rollback()
        
        logger.info(
            f"Analysis execution complete for {analysis_id}: "
            f"duration={state['duration_seconds']:.1f}s, "
            f"overall_progress={state['overall_progress']}"
        )
    
    except Exception as e:
        logger.error(f"Error during analysis execution: {str(e)}", exc_info=True)
        state["stage"] = AnalysisStage.ERROR
        state["errors"].append({
            "stage": "execution",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@router.get("/{analysis_id}/progress")
async def get_analysis_progress(analysis_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get real-time execution progress of 3 agents
    
    Returns: overall progress percentage, per-agent progress, current stage, and error (if any)
    """
    try:
        # First check memory store
        state = ANALYSIS_STORE.get(analysis_id)
        
        # If not in memory, try database
        if not state:
            analysis_record = db.query(AnalysisResult).filter(
                AnalysisResult.id == UUID(analysis_id)
            ).first()
            
            if not analysis_record:
                raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
            
            # Return database record as progress
            return {
                "analysis_id": analysis_id,
                "stage": AnalysisStage.ANALYSIS_COMPLETE,
                "overall_progress": 1.0,
                "agent_progress": {
                    "portfolio_analysis": 1.0,
                    "risk_assessment": 1.0,
                    "investment_recommendation": 1.0
                },
                "agent_status": {
                    "portfolio_analysis": "complete",
                    "risk_assessment": "complete",
                    "investment_recommendation": "complete"
                },
                "is_complete": True,
                "source": "database"
            }
        
        # In-memory state
        response = {
            "analysis_id": analysis_id,
            "stage": state["stage"],
            "overall_progress": state.get("overall_progress", 0.0),
            "agent_progress": {
                "portfolio_analysis": state.get("stage_progress", {}).get("portfolio", 0.0),
                "risk_assessment": state.get("stage_progress", {}).get("risk", 0.0),
                "investment_recommendation": state.get("stage_progress", {}).get("recommendation", 0.0)
            },
            "agent_status": {
                "portfolio_analysis": state.get("stage_status", {}).get("portfolio", "queued"),
                "risk_assessment": state.get("stage_status", {}).get("risk", "queued"),
                "investment_recommendation": state.get("stage_status", {}).get("recommendation", "queued")
            },
            "is_complete": state["stage"] == AnalysisStage.ANALYSIS_COMPLETE,
            "source": "memory"
        }
        
        # Include error details if there's an error
        if state["stage"] == AnalysisStage.ERROR and state.get("errors"):
            response["errors"] = state["errors"]
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{analysis_id}/results")
async def get_analysis_results(analysis_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get final analysis results and summaries
    
    Only available after execution is complete.
    Fetches from memory store first, then from database if not in memory.
    
    Returns: All metrics, trades, summaries, and rationale
    """
    try:
        # First check memory store
        state = ANALYSIS_STORE.get(analysis_id)
        
        # If not in memory, try database
        if not state:
            analysis_record = db.query(AnalysisResult).filter(
                AnalysisResult.id == UUID(analysis_id)
            ).first()
            
            if not analysis_record:
                raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
            
            # Parse JSON fields from database record
            # SQLAlchemy automatically deserializes JSON columns to dicts,
            # so only call json.loads() if the value is a string
            def parse_json_field(field_value):
                if field_value is None:
                    return {}
                if isinstance(field_value, str):
                    return json.loads(field_value)
                return field_value  # Already a dict
            
            portfolio_metrics = parse_json_field(analysis_record.portfolio_metrics_json)
            risk_metrics = parse_json_field(analysis_record.risk_metrics_json)
            recommendation = parse_json_field(analysis_record.recommendation_json)
            metrics_summary = parse_json_field(analysis_record.metrics_summary_json)
            rationale = parse_json_field(analysis_record.rationale_json)
            
            # Return database record
            return {
                "analysis_id": analysis_id,
                "created_at": analysis_record.created_at.isoformat() if analysis_record.created_at else None,
                "duration_seconds": analysis_record.duration_seconds,
                "source": "database",
                
                "client_info": {
                    "risk_profile": analysis_record.risk_profile,
                    "household_income": analysis_record.household_income,
                    "cash_on_hand": analysis_record.cash_on_hand,
                    "monthly_investable_income": analysis_record.monthly_investable_income,
                    "tax_status": analysis_record.tax_status,
                    "investment_horizon_months": analysis_record.investment_horizon_months,
                    "liquidity_needs_pct": analysis_record.liquidity_needs_pct,
                    "implementation_scenario": analysis_record.implementation_scenario,
                    "primary_goal": analysis_record.primary_goal
                },
                
                "portfolio_analysis": {
                    "current_allocation": portfolio_metrics.get("allocation"),
                    "portfolio_value": portfolio_metrics.get("portfolio_value"),
                    "diversification_score": portfolio_metrics.get("diversification_score"),
                    "concentration_risk": portfolio_metrics.get("concentration_risk"),
                    "sector_exposure": portfolio_metrics.get("sector_exposure"),
                    "asset_class_exposure": portfolio_metrics.get("asset_class_exposure")
                },
                
                "risk_assessment": {
                    "sharpe_ratio": risk_metrics.get("sharpe_ratio"),
                    "sortino_ratio": risk_metrics.get("sortino_ratio"),
                    "volatility": risk_metrics.get("volatility"),
                    "beta": risk_metrics.get("beta"),
                    "max_drawdown": risk_metrics.get("max_drawdown"),
                    "var_95": risk_metrics.get("var_95"),
                    "cvar_95": risk_metrics.get("cvar_95"),
                    "risk_level": risk_metrics.get("risk_level")
                },
                
                "recommendation": {
                    "recommended_allocation": recommendation.get("recommended_allocation"),
                    "projected_return": recommendation.get("projected_return"),
                    "projected_volatility": recommendation.get("projected_volatility"),
                    "projected_sharpe": recommendation.get("projected_sharpe"),
                    "rebalancing_trades": recommendation.get("rebalancing_trades"),
                    "implementation_cost": recommendation.get("implementation_cost"),
                    "tax_impact": recommendation.get("tax_impact"),
                    "execution_plan": recommendation.get("execution_plan")
                },
                
                "summaries": {
                    "metrics_explanation": metrics_summary,
                    "recommendation_rationale": rationale
                }
            }
        
        # In-memory state
        if state["stage"] != AnalysisStage.ANALYSIS_COMPLETE:
            raise HTTPException(
                status_code=400,
                detail=f"Results not available until analysis is complete (current stage: {state['stage']})"
            )
        
        return {
            "analysis_id": analysis_id,
            "created_at": state["created_at"],
            "duration_seconds": state.get("duration_seconds"),
            "source": "memory",
            
            # Client Info (Risk & Goals Assessment)
            "client_info": {
                "risk_profile": state.get("risk_profile"),
                "household_income": state.get("household_income"),
                "cash_on_hand": state.get("cash_on_hand", 0.0),
                "monthly_investable_income": state.get("monthly_investable_income", 0.0),
                "tax_status": state.get("tax_status"),
                "investment_horizon_months": state.get("investment_horizon_months"),
                "liquidity_needs_pct": state.get("liquidity_needs_pct", 0.0),
                "implementation_scenario": state.get("implementation_scenario"),
                "primary_goal": state.get("primary_goal")
            },
            
            # Portfolio Analysis Results
            "portfolio_analysis": {
                "current_allocation": state.get("allocation"),
                "portfolio_value": state.get("portfolio_value"),
                "diversification_score": state.get("diversification_score"),
                "concentration_risk": state.get("concentration_risk"),
                "sector_exposure": state.get("sector_exposure"),
                "asset_class_exposure": state.get("asset_class_exposure")
            },
            
            # Risk Assessment Results
            "risk_assessment": {
                "sharpe_ratio": state.get("sharpe_ratio"),
                "sortino_ratio": state.get("sortino_ratio"),
                "volatility": state.get("volatility"),
                "beta": state.get("beta"),
                "max_drawdown": state.get("max_drawdown"),
                "var_95": state.get("var_95"),
                "cvar_95": state.get("cvar_95"),
                "risk_level": state.get("risk_level")
            },
            
            # Investment Recommendation Results
            "recommendation": {
                "recommended_allocation": state.get("recommended_allocation"),
                "projected_return": state.get("projected_return"),
                "projected_volatility": state.get("projected_volatility"),
                "projected_sharpe": state.get("projected_sharpe"),
                "rebalancing_trades": state.get("rebalancing_trades"),
                "implementation_cost": state.get("implementation_cost"),
                "tax_impact": state.get("tax_impact"),
                "execution_plan": state.get("execution_plan")
            },
            
            # Summaries & Explanations
            "summaries": {
                "metrics_explanation": state.get("metrics_summary"),
                "recommendation_rationale": state.get("recommendation_rationale")
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{analysis_id}/ask")
async def cross_question(
    analysis_id: str,
    request_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Post-analysis cross-questioning (Advisor Copilot)
    
    Ask follow-up questions with access to all computed metrics and recommendations.
    Examples:
    - "What if I increase bond allocation to 50%?"
    - "How does this compare to my current portfolio?"
    - "Why was this fund excluded from the recommendation?"
    
    Request body:
    {
        "question": "What if I wanted more income from dividends?"
    }
    
    Returns: Answer with metric context
    
    Works with both in-memory and database-persisted analyses.
    """
    try:
        state = ANALYSIS_STORE.get(analysis_id)
        
        # If not in memory, try database
        if not state:
            analysis_record = db.query(AnalysisResult).filter(
                AnalysisResult.id == UUID(analysis_id)
            ).first()
            
            if not analysis_record:
                raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
            
            question = request_data.get("question", "").strip()
            if not question:
                raise HTTPException(status_code=400, detail="question required")
            
            # Handle database records: reconstruct state from stored JSON fields
            try:
                # Extract all stored metrics
                portfolio_metrics = analysis_record.portfolio_metrics_json or {}
                risk_metrics = analysis_record.risk_metrics_json or {}
                recommendation = analysis_record.recommendation_json or {}
                
                # Build context for LLM (same structure as in-memory path)
                context = {
                    "current_allocation": portfolio_metrics.get("allocation", {}),
                    "recommended_allocation": recommendation.get("recommended_allocation", {}),
                    "risk_profile": analysis_record.risk_profile,
                    "risk_metrics": {
                        "sharpe_ratio": risk_metrics.get("sharpe_ratio"),
                        "volatility": risk_metrics.get("volatility"),
                        "beta": risk_metrics.get("beta")
                    },
                    "recommended_trades": recommendation.get("rebalancing_trades", [])
                }
                
                # Generate answer using LLM with full context
                from app.services.llm_wrapper import LLMWrapper
                llm = LLMWrapper(model_name="gpt-oss-120b")
                
                context_prompt = f"""
You are an expert investment advisor assistant with access to the following analysis results:

Current Portfolio Allocation:
{portfolio_metrics.get('allocation', {})}

Recommended Allocation:
{recommendation.get('recommended_allocation', {})}

Risk Profile: {analysis_record.risk_profile or 'moderate'}

Key Metrics:
- Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 0):.2f}
- Volatility: {risk_metrics.get('volatility', 0):.2%}
- Beta: {risk_metrics.get('beta', 1.0):.2f}
- Max Drawdown: {risk_metrics.get('max_drawdown', 0):.2%}
- Diversification Score: {portfolio_metrics.get('diversification_score', 0):.2f}/1.0

Recommended Trades:
{recommendation.get('rebalancing_trades', [])}

Investment Plan Summary:
{recommendation.get('execution_plan', 'See recommendations above')}

User Question: {question}

Please provide a thoughtful, professional answer to the user's question using the available metrics and context.
Be specific with numbers and references to their portfolio analysis. If the question involves a hypothetical scenario,
explain how it would affect their current situation based on the data above.
"""
                
                answer = await llm.generate(
                    prompt=context_prompt,
                    use_case="cross_question",
                    temperature=0.7
                )
                
                return {
                    "analysis_id": analysis_id,
                    "question": question,
                    "answer": answer,
                    "metrics_referenced": {
                        "current_allocation": portfolio_metrics.get("allocation", {}),
                        "recommended_allocation": recommendation.get("recommended_allocation", {}),
                        "sharpe_ratio": risk_metrics.get("sharpe_ratio"),
                        "volatility": risk_metrics.get("volatility")
                    },
                    "source": "database"
                }
            
            except Exception as e:
                logger.error(f"Error cross-questioning database analysis {analysis_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing cross-question: {str(e)}"
                )
        
        # In-memory state
        if state["stage"] != AnalysisStage.ANALYSIS_COMPLETE:
            raise HTTPException(
                status_code=400,
                detail="Cross-questioning only available after analysis complete"
            )
        
        question = request_data.get("question", "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="question required")
        
        # Prepare context for LLM
        context = {
            "current_allocation": state.get("allocation"),
            "recommended_allocation": state.get("recommended_allocation"),
            "risk_profile": state.get("risk_profile"),
            "risk_metrics": {
                "sharpe_ratio": state.get("sharpe_ratio"),
                "volatility": state.get("volatility"),
                "beta": state.get("beta")
            },
            "recommended_trades": state.get("rebalancing_trades")
        }
        
        # Generate answer using LLM with full context
        from app.services.llm_wrapper import LLMWrapper
        llm = LLMWrapper(model_name="gpt-oss-120b")
        
        context_prompt = f"""
You are an expert investment advisor assistant with access to the following analysis results:

Current Portfolio Allocation:
{state.get('allocation', {})}

Recommended Allocation:
{state.get('recommended_allocation', {})}

Risk Profile: {state.get('risk_profile', 'moderate')}

Key Metrics:
- Sharpe Ratio: {state.get('sharpe_ratio', 0):.2f}
- Volatility: {state.get('volatility', 0):.2%}
- Beta: {state.get('beta', 1.0):.2f}
- Max Drawdown: {state.get('max_drawdown', 0):.2%}
- Diversification Score: {state.get('diversification_score', 0):.2f}/1.0

Recommended Trades:
{state.get('rebalancing_trades', [])}

Investment Plan Summary:
{state.get('execution_plan', 'See recommendations above')}

User Question: {question}

Please provide a thoughtful, professional answer to the user's question using the available metrics and context.
Be specific with numbers and references to their portfolio analysis. If the question involves a hypothetical scenario,
explain how it would affect their current situation based on the data above.
"""
        
        answer = await llm.generate(
            prompt=context_prompt,
            use_case="cross_question",
            temperature=0.7
        )
        
        # Add to copilot history
        state["copilot_messages"].append({"role": "user", "content": question})
        state["copilot_messages"].append({"role": "assistant", "content": answer})
        
        return {
            "analysis_id": analysis_id,
            "question": question,
            "answer": answer,
            "metrics_referenced": {
                "current_allocation": state.get("allocation"),
                "recommended_allocation": state.get("recommended_allocation"),
                "sharpe_ratio": state.get("sharpe_ratio")
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing cross-question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



    """
    Get current status of analysis workflow
    
    Returns: current stage, completion flags, and results
    """
    try:
        if analysis_id not in ANALYSIS_STORE:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        state = ANALYSIS_STORE[analysis_id]
        
        return {
            "analysis_id": analysis_id,
            "stage": state["stage"],
            "status": "in_progress" if state["stage"] != AnalysisStage.COMPLETE else "complete",
            "profile_complete": state.get("profile_complete", False),
            "risk_assessment_complete": state.get("risk_assessment_complete", False),
            "created_at": state["created_at"],
            "duration_seconds": state.get("duration_seconds"),
            "results": {
                "allocation": state.get("allocation"),
                "recommended_allocation": state.get("recommended_allocation"),
                "risk_profile": state.get("risk_profile"),
                "sharpe_ratio": state.get("sharpe_ratio"),
                "projected_return": state.get("projected_return"),
                "implementation_cost": state.get("implementation_cost"),
                "execution_plan": state.get("execution_plan")
            } if state["stage"] in [AnalysisStage.COMPLETE, AnalysisStage.ADVISOR_COPILOT] else None,
            "errors": state["errors"],
            "warnings": state["warnings"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

