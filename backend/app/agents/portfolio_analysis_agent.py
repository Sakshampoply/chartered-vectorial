"""
Portfolio Analysis Agent (Stage 3, Agent 1 - 25% weight)

Responsibilities:
- Analyze portfolio composition and diversification
- Call PortfolioAnalyzer service with real holdings
- Calculate: allocation, sectors, concentration risks, diversification score
- Track execution from 0→100% progress
- Generate LLM summary of findings
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.agents.state import AnalysisState
from app.services.portfolio_analyzer import PortfolioAnalyzer
from app.services.llm_wrapper import LLMWrapper
from app.models.client import Portfolio
from app.database import get_db

logger = logging.getLogger(__name__)


class PortfolioAnalysisAgent:
    """
    Agent 1: Portfolio Analysis (25% weight in overall progress)
    
    Input: portfolio_id + holdings
    Output: allocation, sectors, diversification, concentration risks + LLM summary
    """
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None, db: Optional[Session] = None):
        """
        Initialize agent
        
        Args:
            llm_wrapper: LLMWrapper for LLM-based summaries
            db: Database session for loading portfolio
        """
        self.llm = llm_wrapper or LLMWrapper(model_name="openai/gpt-oss-120b")
        self.db = db
        self.logger = logger
    
    async def execute(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Execute portfolio analysis with progress tracking
        
        Args:
            state: Current analysis state with portfolio_id + holdings
            
        Returns:
            Updated metrics dictionary with progress info
        """
        try:
            # Initialize progress
            state["stage_progress"]["portfolio_analysis"] = 0.0
            state["stage_status"]["portfolio_analysis"] = "running"
            
            portfolio_id = state.get("portfolio_id")
            if not portfolio_id:
                raise ValueError("portfolio_id required for analysis")
            
            # Step 1: Load portfolio from DB (10% progress)
            self.logger.info(f"[Portfolio Agent] Loading portfolio {portfolio_id}")
            state["stage_progress"]["portfolio_analysis"] = 0.1
            
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio not found: {portfolio_id}")
            
            holdings = [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "price": h.price,
                    "value": h.value,
                    "asset_class": h.asset_class,
                    "sector": h.sector,
                }
                for h in portfolio.holdings
            ]
            
            if not holdings:
                raise ValueError("No holdings in portfolio")
            
            # Step 2: Compute allocation (30% progress)
            self.logger.info(f"[Portfolio Agent] Computing allocation for {len(holdings)} holdings")
            state["stage_progress"]["portfolio_analysis"] = 0.3
            await asyncio.sleep(0.5)  # Simulate compute time
            
            allocation = PortfolioAnalyzer.compute_asset_allocation(holdings)
            state["allocation"] = allocation
            
            # Step 3: Compute sector exposure (50% progress)
            self.logger.info(f"[Portfolio Agent] Computing sector exposure")
            state["stage_progress"]["portfolio_analysis"] = 0.5
            await asyncio.sleep(0.5)
            
            sector_exposure = PortfolioAnalyzer.compute_sector_allocation(holdings)
            state["sector_exposure"] = sector_exposure or {}
            
            # Step 4: Compute diversification (75% progress)
            self.logger.info(f"[Portfolio Agent] Computing diversification score")
            state["stage_progress"]["portfolio_analysis"] = 0.75
            await asyncio.sleep(0.5)
            
            diversification_score = PortfolioAnalyzer.compute_diversification_score(holdings)
            state["diversification_score"] = diversification_score / 100.0 if diversification_score else 0.5
            state["concentration_risk"] = 1.0 - state["diversification_score"]
            
            # Step 5: Identify concentration risks (90% progress)
            self.logger.info(f"[Portfolio Agent] Identifying concentration risks")
            state["stage_progress"]["portfolio_analysis"] = 0.9
            
            concentration_risks = self._identify_concentration_risks(holdings, allocation)
            state["portfolio_concentration_risks"] = concentration_risks
            
            # Step 6: Generate LLM summary (100% progress)
            self.logger.info(f"[Portfolio Agent] Generating LLM summary")
            state["stage_progress"]["portfolio_analysis"] = 1.0
            await asyncio.sleep(0.3)
            
            summary = await self._generate_summary(state, holdings)
            state["portfolio_summary"] = summary
            
            # Mark complete
            state["stage_status"]["portfolio_analysis"] = "complete"
            
            self.logger.info("[Portfolio Agent] ✓ Complete")
            
            return {
                "status": "complete",
                "metrics": {
                    "allocation": allocation,
                    "sector_exposure": sector_exposure or {},
                    "diversification_score": diversification_score,
                    "concentration_risks": concentration_risks,
                    "portfolio_value": portfolio.total_value,
                    "holdings_count": len(holdings),
                    "asset_classes": len(allocation),
                },
                "summary": summary,
            }
        
        except Exception as e:
            self.logger.error(f"[Portfolio Agent] Error: {str(e)}")
            state["stage_status"]["portfolio_analysis"] = "error"
            state["stage_progress"]["portfolio_analysis"] = 0.0
            raise
    
    def _identify_concentration_risks(
        self, holdings: list, allocation: Dict[str, float]
    ) -> list:
        """
        Identify holdings/sectors with concentration risks
        
        Rules:
        - Single holding >10%
        - Sector >25%
        """
        risks = []
        total_value = sum(h["value"] for h in holdings)
        
        # Individual holding concentration
        for holding in holdings:
            pct = (holding["value"] / total_value * 100) if total_value > 0 else 0
            if pct > 10:
                risks.append(f"Position {holding['ticker']} is {pct:.1f}% of portfolio (>10%)")
        
        # Sector concentration (if available)
        sectors = {}
        for holding in holdings:
            sector = holding.get("sector") or "Unknown"
            sectors.setdefault(sector, 0)
            sectors[sector] += holding["value"]
        
        for sector, value in sectors.items():
            pct = (value / total_value * 100) if total_value > 0 else 0
            if pct > 25:
                risks.append(f"Sector {sector} is {pct:.1f}% of portfolio (>25%)")
        
        return risks
    
    async def _generate_summary(self, state: AnalysisState, holdings: list) -> str:
        """Generate LLM summary of portfolio analysis"""
        try:
            prompt = f"""
Given this portfolio analysis, provide a 2-3 sentence plain English summary:

Portfolio Composition:
- Total Holdings: {len(holdings)}
- Asset Classes: {list(state.get('allocation', {}).keys())}
- Allocation: {state.get('allocation', {})}
- Sector Exposure: {state.get('sector_exposure', {})}

Diversification & Risk:
- Diversification Score: {state.get('diversification_score', 0):.2f}/1.0
- Concentration Risks: {state.get('portfolio_concentration_risks', [])}

Provide a brief, professional summary of the portfolio composition in 2-3 sentences. 
Focus on what this allocation tells us about the portfolio strategy.
"""
            
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.6,
            )
            
            return response.strip()
        
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            return "Portfolio analysis complete. See metrics above for details."
