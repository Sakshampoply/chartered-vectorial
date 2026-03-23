"""
LangGraph Orchestrator for Chartered Vectorial Analysis Workflow

Defines the state machine workflow connecting:
1. Document Ingestion → Chat Intake → Risk Profiling (Stages 1-2)
2. Portfolio Analysis → Risk Assessment → Recommendation (Stages 3-4)
3. Advisor Copilot → Follow-up (Stage 5+)

Uses conditional routing to handle document availability and validation failures.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import logging
import asyncio
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from .state import AnalysisState, AnalysisStage, AnalysisStateFactory
from .tools import ToolExecutor, TOOLS_REGISTRY
from .document_intelligence import DocumentIntelligenceAgent

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """
    LangGraph-based orchestrator for investment analysis workflow
    
    Manages state transitions and conditional routing across 8 stages:
    1. Document Ingestion (optional)
    2. Chat Intake (Stage 1)
    3. Risk Profiling (Stage 2)
    4. Portfolio Analysis (Stage 3)
    5. Risk Assessment (Stage 3)
    6. Recommendation (Stage 4)
    7. Scoring & Feasibility (Stage 4)
    8. Advisor Copilot (Stage 5)
    """
    
    def __init__(self, services: Dict[str, Any], llm_wrapper: Optional["LLMWrapper"] = None):
        """
        Initialize orchestrator with service dependencies
        
        Args:
            services: Dict of service instances
                     e.g., {"portfolio_analyzer": PortfolioAnalyzer()}
            llm_wrapper: Optional LLMWrapper for agents
        """
        # Lazy import to avoid circular dependency
        from app.services.llm_wrapper import LLMWrapper
        
        self.services = services
        self.llm = llm_wrapper or LLMWrapper(model_name="gpt-oss-120b")
        self.tool_executor = ToolExecutor(services)
        self.document_agent = DocumentIntelligenceAgent(llm_wrapper=self.llm)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        
        workflow = StateGraph(AnalysisState)
        
        # ====================================================================
        # NODE DEFINITIONS
        # ====================================================================
        
        # Node 1: Document Ingestion (optional, Stage 1)
        workflow.add_node("document_ingestion", self._node_document_ingestion)
        
        # Node 2: Chat Intake (required, Stage 1)
        workflow.add_node("chat_intake", self._node_chat_intake)
        
        # Node 3: Risk Profiling (progressive, Stage 2)
        workflow.add_node("risk_profiling", self._node_risk_profiling)
        
        # Node 4: Portfolio Analysis (Stage 3)
        workflow.add_node("portfolio_analysis", self._node_portfolio_analysis)
        
        # Node 5: Risk Assessment (Stage 3)
        workflow.add_node("risk_assessment", self._node_risk_assessment)
        
        # Node 6: Recommendation Strategy (Stage 4)
        workflow.add_node("recommendation", self._node_recommendation)
        
        # Node 7: Scoring & Feasibility (Stage 4)
        workflow.add_node("scoring", self._node_scoring)
        
        # Node 8: Advisor Copilot (Stage 5, optional)
        workflow.add_node("advisor_copilot", self._node_advisor_copilot)
        
        # ====================================================================
        # EDGE DEFINITIONS (routing logic)
        # ====================================================================
        
        # Entry point: Documents provided → document_ingestion, else → chat_intake
        workflow.add_conditional_edges(
            START,
            self._route_start,
            {
                "document_ingestion": "document_ingestion",
                "chat_intake": "chat_intake"
            }
        )
        
        # Document ingestion → Chat intake (always)
        workflow.add_edge("document_ingestion", "chat_intake")
        
        # Chat intake → Risk profiling (if profile complete)
        # else → loop back to chat_intake
        workflow.add_conditional_edges(
            "chat_intake",
            self._route_chat_intake,
            {
                "risk_profiling": "risk_profiling",
                "chat_intake": "chat_intake"  # Loop for follow-ups
            }
        )
        
        # Risk profiling → Portfolio analysis (if >= 70% complete)
        # else → loop back to risk_profiling
        workflow.add_conditional_edges(
            "risk_profiling",
            self._route_risk_profiling,
            {
                "portfolio_analysis": "portfolio_analysis",
                "risk_profiling": "risk_profiling"  # Loop for more questions
            }
        )
        
        # Portfolio analysis → Risk assessment (always, parallel computation)
        workflow.add_edge("portfolio_analysis", "risk_assessment")
        
        # Risk assessment → Recommendation (always)
        workflow.add_edge("risk_assessment", "recommendation")
        
        # Recommendation → Scoring (always)
        workflow.add_edge("recommendation", "scoring")
        
        # Scoring → Advisor Copilot or END
        workflow.add_conditional_edges(
            "scoring",
            self._route_scoring,
            {
                "advisor_copilot": "advisor_copilot",
                END: END
            }
        )
        
        # Advisor Copilot → END
        workflow.add_edge("advisor_copilot", END)
        
        return workflow.compile()
    
    # ========================================================================
    # NODE IMPLEMENTATIONS
    # ========================================================================
    
    def _node_document_ingestion(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 1: Extract data from uploaded documents
        
        Uses DocumentIntelligenceAgent to process all uploaded files.
        Sets extracted_holdings for later portfolio creation.
        """
        logger.info(f"[Document Ingestion] Starting for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "document_ingestion_started")
        
        try:
            if not state.get("uploaded_documents"):
                logger.warning("No documents provided, skipping ingestion")
                return state
            
            # Use DocumentIntelligenceAgent to process documents
            # Note: LangGraph nodes are synchronous, but agent is async
            # Run async agent in sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            state = loop.run_until_complete(
                self.document_agent.process_documents(state)
            )
            
            state["stage"] = AnalysisStage.DOCUMENT_INGESTION
            state = AnalysisStateFactory.log_step(
                state,
                "document_ingestion_complete",
                {
                    "holdings_extracted": len(state["extracted_holdings"]),
                    "confidence": state.get("document_extraction_confidence"),
                    "method": state.get("document_extraction_method")
                }
            )
            
        except Exception as e:
            logger.error(f"Document ingestion node error: {str(e)}")
            state = AnalysisStateFactory.add_error(state, "document_ingestion", str(e))
        
        return state
    
    def _node_chat_intake(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 1: Chat-driven client intake
        
        Collects: name, age, email, phone, investment goals, existing portfolio data.
        Multi-turn conversation until profile_complete = True.
        
        NOTE: In Phase 2 implementation, this will integrate ChatIntakeAgent
        """
        logger.info(f"[Chat Intake] Processing for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "chat_intake_started")
        
        state["stage"] = AnalysisStage.CHAT_INTAKE
        
        # TODO: Integrate ChatIntakeAgent here
        # For now: placeholder that simulates completion
        state["profile_complete"] = True
        state["client_name"] = state.get("client_name") or "Client Name"
        state["client_age"] = state.get("client_age") or 45
        state["investment_goals"] = state.get("investment_goals") or ["retirement", "wealth_growth"]
        state["chat_messages_count"] += 1
        
        state = AnalysisStateFactory.log_step(
            state,
            "chat_intake_complete",
            {"profile_complete": state["profile_complete"]}
        )
        
        return state
    
    def _node_risk_profiling(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 2: Progressive risk assessment questionnaire
        
        Asks 8 questions progressively. Requires >= 70% answered to proceed.
        Computes risk_profile (conservative/moderate/aggressive) and risk_score (0-100).
        
        NOTE: In Phase 3 implementation, this will integrate RiskProfilerAgent
        """
        logger.info(f"[Risk Profiling] Processing for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "risk_profiling_started")
        
        state["stage"] = AnalysisStage.RISK_PROFILING
        
        # TODO: Integrate RiskProfilerAgent here
        # For now: placeholder that simulates completion
        state["risk_questions_answered"] += 1
        state["risk_assessment_complete"] = state["risk_questions_answered"] >= 8
        
        # Placeholder risk profile
        if not state.get("risk_profile"):
            state["risk_profile"] = "moderate"
            state["risk_score"] = 50
        
        state = AnalysisStateFactory.log_step(
            state,
            "risk_profiling_complete",
            {"risk_profile": state["risk_profile"], "risk_score": state["risk_score"]}
        )
        
        return state
    
    def _node_portfolio_analysis(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 3: Portfolio composition and diversification analysis
        
        Calls portfolio_analysis tool to compute:
        - Current allocation (%)
        - Concentration risk
        - Diversification score
        - Sector/asset class exposure
        """
        logger.info(f"[Portfolio Analysis] Starting for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "portfolio_analysis_started")
        
        state["stage"] = AnalysisStage.PORTFOLIO_ANALYSIS
        
        # Create portfolio if holdings extracted from documents
        if state.get("extracted_holdings"):
            # TODO: Create portfolio in database from extracted_holdings
            # This would set state["portfolio_id"]
            pass
        
        # Execute portfolio analysis tool
        try:
            if state.get("portfolio_id"):
                result = self.tool_executor.execute_tool(
                    "portfolio_analysis",
                    {
                        "portfolio_id": state["portfolio_id"],
                        "rebalance": True
                    }
                )
                
                if result["status"] == "success":
                    data = result["data"]
                    state["allocation"] = data.get("allocation")
                    state["concentration_risk"] = data.get("concentration_risk")
                    state["diversification_score"] = data.get("diversification_score")
                    state["sector_exposure"] = data.get("sector_exposure")
                    state["asset_class_exposure"] = data.get("asset_class_exposure")
                    state["rebalancing_needed"] = data.get("rebalancing_needed", False)
                else:
                    state = AnalysisStateFactory.add_error(
                        state,
                        "portfolio_analysis",
                        result.get("error", "Unknown error")
                    )
        
        except Exception as e:
            logger.error(f"Portfolio analysis error: {str(e)}")
            state = AnalysisStateFactory.add_error(state, "portfolio_analysis", str(e))
        
        state = AnalysisStateFactory.log_step(
            state,
            "portfolio_analysis_complete",
            {"allocation": state.get("allocation")}
        )
        
        return state
    
    def _node_risk_assessment(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 3: Calculate risk metrics
        
        Calls risk_assessment tool to compute:
        - Sharpe ratio, Sortino ratio
        - Volatility, Beta, Max Drawdown
        - VaR and CVaR
        - Inferred risk level
        """
        logger.info(f"[Risk Assessment] Starting for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "risk_assessment_started")
        
        state["stage"] = AnalysisStage.RISK_ASSESSMENT
        
        try:
            if state.get("portfolio_id"):
                result = self.tool_executor.execute_tool(
                    "risk_assessment",
                    {
                        "portfolio_id": state["portfolio_id"],
                        "client_id": state["client_id"]
                    }
                )
                
                if result["status"] == "success":
                    data = result["data"]
                    state["sharpe_ratio"] = data.get("sharpe_ratio")
                    state["sortino_ratio"] = data.get("sortino_ratio")
                    state["volatility"] = data.get("volatility")
                    state["beta"] = data.get("beta")
                    state["max_drawdown"] = data.get("max_drawdown")
                    state["var_95"] = data.get("var_95")
                    state["cvar_95"] = data.get("cvar_95")
                    state["risk_level"] = data.get("risk_level")
                else:
                    state = AnalysisStateFactory.add_error(
                        state,
                        "risk_assessment",
                        result.get("error", "Unknown error")
                    )
        
        except Exception as e:
            logger.error(f"Risk assessment error: {str(e)}")
            state = AnalysisStateFactory.add_error(state, "risk_assessment", str(e))
        
        state = AnalysisStateFactory.log_step(
            state,
            "risk_assessment_complete",
            {"sharpe_ratio": state.get("sharpe_ratio"), "volatility": state.get("volatility")}
        )
        
        return state
    
    def _node_recommendation(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 4: Generate portfolio optimization recommendation
        
        Calls recommendation_strategy tool to compute:
        - Recommended allocation
        - Expected return/volatility
        - Rebalancing trades
        - Implementation cost and tax impact
        - Timeline for implementation
        """
        logger.info(f"[Recommendation] Starting for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "recommendation_started")
        
        state["stage"] = AnalysisStage.RECOMMENDATION
        
        try:
            if state.get("portfolio_id"):
                result = self.tool_executor.execute_tool(
                    "recommendation_strategy",
                    {
                        "portfolio_id": state["portfolio_id"],
                        "risk_profile": state.get("risk_profile", "moderate"),
                        "goals": state.get("investment_goals", [])
                    }
                )
                
                if result["status"] == "success":
                    data = result["data"]
                    state["recommended_allocation"] = data.get("recommended_allocation")
                    state["projected_return"] = data.get("projected_return")
                    state["projected_volatility"] = data.get("projected_volatility")
                    state["projected_sharpe"] = data.get("projected_sharpe")
                    state["rebalancing_trades"] = data.get("rebalancing_trades", [])
                    state["implementation_cost"] = data.get("implementation_cost")
                    state["tax_impact"] = data.get("tax_impact")
                    state["expected_annual_benefit"] = data.get("expected_annual_benefit")
                    state["implementation_timeline"] = data.get("implementation_timeline")
                else:
                    state = AnalysisStateFactory.add_error(
                        state,
                        "recommendation",
                        result.get("error", "Unknown error")
                    )
        
        except Exception as e:
            logger.error(f"Recommendation error: {str(e)}")
            state = AnalysisStateFactory.add_error(state, "recommendation", str(e))
        
        state = AnalysisStateFactory.log_step(
            state,
            "recommendation_complete",
            {"recommended_allocation": state.get("recommended_allocation")}
        )
        
        return state
    
    def _node_scoring(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 4: Score recommendation for feasibility and impact
        
        Calls scoring tool to evaluate:
        - Feasibility score (0-1)
        - Impact score (0-1)
        - Operational burden (low/medium/high)
        - Any constraint violations
        """
        logger.info(f"[Scoring] Starting for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "scoring_started")
        
        state["stage"] = AnalysisStage.SCORING
        
        try:
            if state.get("portfolio_id") and state.get("recommended_allocation"):
                result = self.tool_executor.execute_tool(
                    "score_and_feasibility",
                    {
                        "portfolio_id": state["portfolio_id"],
                        "proposed_changes": state["recommended_allocation"],
                        "implementation_cost_budget": 1000  # TODO: Get from client preferences
                    }
                )
                
                if result["status"] == "success":
                    data = result["data"]
                    state["feasibility_score"] = data.get("feasibility_score")
                    state["impact_score"] = data.get("impact_score")
                    state["operational_burden"] = data.get("operational_burden")
                    state["constraints_violated"] = data.get("constraints_violated", [])
                else:
                    state = AnalysisStateFactory.add_error(
                        state,
                        "scoring",
                        result.get("error", "Unknown error")
                    )
        
        except Exception as e:
            logger.error(f"Scoring error: {str(e)}")
            state = AnalysisStateFactory.add_error(state, "scoring", str(e))
        
        # Generate execution plan
        if state.get("feasibility_score", 0) >= 0.7:
            state["execution_plan"] = self._generate_execution_plan(state)
        
        state = AnalysisStateFactory.log_step(
            state,
            "scoring_complete",
            {"feasibility_score": state.get("feasibility_score")}
        )
        
        return state
    
    def _node_advisor_copilot(self, state: AnalysisState) -> AnalysisState:
        """
        Stage 5: Advisor Copilot for Q&A and what-if analysis
        
        Prepares analysis snapshot for copilot reasoning.
        In Phase 6 implementation, will integrate AdvisorCopilotAgent for:
        - Answering questions about results
        - What-if scenario exploration
        - Implementation guidance
        """
        logger.info(f"[Advisor Copilot] Starting for analysis {state['analysis_id']}")
        state = AnalysisStateFactory.log_step(state, "advisor_copilot_started")
        
        state["stage"] = AnalysisStage.ADVISOR_COPILOT
        
        # Create context snapshot for copilot
        state["copilot_context"] = {
            "portfolio_value": state.get("portfolio_value"),
            "current_allocation": state.get("allocation"),
            "recommended_allocation": state.get("recommended_allocation"),
            "risk_profile": state.get("risk_profile"),
            "sharpe_ratio": state.get("sharpe_ratio"),
            "projected_return": state.get("projected_return"),
            "implementation_cost": state.get("implementation_cost"),
            "tax_impact": state.get("tax_impact")
        }
        
        # TODO: Integrate AdvisorCopilotAgent here
        
        state = AnalysisStateFactory.log_step(state, "advisor_copilot_ready")
        
        return state
    
    # ========================================================================
    # ROUTING FUNCTIONS
    # ========================================================================
    
    def _route_start(self, state: AnalysisState) -> str:
        """Route START → document_ingestion OR chat_intake"""
        if state.get("uploaded_documents"):
            return "document_ingestion"
        return "chat_intake"
    
    def _route_chat_intake(self, state: AnalysisState) -> str:
        """Route chat_intake → risk_profiling OR loop"""
        if state.get("profile_complete"):
            return "risk_profiling"
        return "chat_intake"
    
    def _route_risk_profiling(self, state: AnalysisState) -> str:
        """Route risk_profiling → portfolio_analysis OR loop"""
        completion_ratio = state.get("risk_questions_answered", 0) / 8
        if completion_ratio >= 0.7:
            return "portfolio_analysis"
        return "risk_profiling"
    
    def _route_scoring(self, state: AnalysisState) -> str:
        """Route scoring → advisor_copilot OR END"""
        # If feasibility score is good, offer copilot for Q&A
        if state.get("feasibility_score", 0) >= 0.7:
            return "advisor_copilot"
        return END
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _generate_execution_plan(self, state: AnalysisState) -> str:
        """Generate human-readable execution plan"""
        allocation = state.get("recommended_allocation", {})
        timeline = state.get("implementation_timeline", "immediate")
        cost = state.get("implementation_cost", 0)
        
        plan = f"""
EXECUTION PLAN
==============

Timeline: {timeline}
Estimated Cost: ${cost:,.2f}

Changes Required:
"""
        
        for ticker, weight in allocation.items():
            current = state.get("allocation", {}).get(ticker, 0)
            if current != weight:
                action = "Increase" if weight > current else "Decrease"
                plan += f"  • {action} {ticker} from {current:.1%} to {weight:.1%}\n"
        
        plan += f"""
Tax Impact: ${state.get('tax_impact', 0):,.2f}
Expected Annual Benefit: ${state.get('expected_annual_benefit', 0):,.2f}
"""
        
        return plan.strip()
    
    async def execute(self, state: AnalysisState) -> AnalysisState:
        """
        Execute the analysis workflow
        
        Args:
            state: Initial analysis state with client_id and optional uploaded_documents
            
        Returns:
            Final state with all analysis results
        """
        logger.info(f"Starting analysis workflow: {state['analysis_id']}")
        start_time = datetime.now()
        
        try:
            # Run graph (synchronous compile returns callable)
            final_state = self.graph.invoke(state)
            
            duration = (datetime.now() - start_time).total_seconds()
            final_state["duration_seconds"] = duration
            
            logger.info(
                f"Analysis complete: {final_state['analysis_id']} "
                f"(duration: {duration:.1f}s, tokens: {final_state['token_count']})"
            )
            
            return final_state
        
        except Exception as e:
            logger.error(f"Analysis workflow error: {str(e)}")
            state = AnalysisStateFactory.add_error(state, "orchestrator", str(e))
            return state
