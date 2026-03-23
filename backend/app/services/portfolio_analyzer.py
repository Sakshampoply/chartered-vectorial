import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from app.models.client import Holding, AssetClass
import logging

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    """Analyze portfolio composition, allocations, and diversification"""

    @staticmethod
    def compute_asset_allocation(holdings: List[Dict]) -> Dict[str, float]:
        """
        Compute what % of portfolio is in each asset class.
        Returns normalized percentages summing to 100%.
        """
        try:
            if not holdings:
                return {}
            
            # Convert to DataFrame for easier calculation
            df = pd.DataFrame(holdings)
            df['value'] = df['quantity'] * df['price']
            
            total_value = df['value'].sum()
            if total_value <= 0:
                return {}
            
            allocation = {}
            for asset_class in AssetClass:
                class_value = df[df['asset_class'] == asset_class.value]['value'].sum()
                allocation[asset_class.value] = round((class_value / total_value) * 100, 2)
            
            return allocation
        except Exception as e:
            logger.error(f"Error computing asset allocation: {e}")
            return {}

    @staticmethod
    def compute_sector_allocation(holdings: List[Dict]) -> Dict[str, float]:
        """
        Compute what % of portfolio is in each sector.
        Returns normalized percentages.
        """
        try:
            if not holdings:
                return {}
            
            df = pd.DataFrame(holdings)
            df['value'] = df['quantity'] * df['price']
            
            total_value = df['value'].sum()
            if total_value <= 0:
                return {}
            
            allocation = {}
            for sector in df['sector'].dropna().unique():
                sector_value = df[df['sector'] == sector]['value'].sum()
                allocation[sector] = round((sector_value / total_value) * 100, 2)
            
            return dict(sorted(allocation.items(), key=lambda x: x[1], reverse=True))
        except Exception as e:
            logger.error(f"Error computing sector allocation: {e}")
            return {}

    @staticmethod
    def compute_diversification_score(holdings: List[Dict]) -> int:
        """
        Compute diversification score (0-100).
        Penalizes high concentration in few holdings or sectors.
        
        Formula:
        base_score = 100 - (top_10_holdings_concentration + sector_concentration_penalty)
        """
        try:
            if not holdings:
                return 0
            
            df = pd.DataFrame(holdings)
            df['value'] = df['quantity'] * df['price']
            
            total_value = df['value'].sum()
            if total_value <= 0:
                return 0
            
            # Calculate individual holding concentrations
            df['pct'] = (df['value'] / total_value) * 100
            df_sorted = df.sort_values('pct', ascending=False)
            
            # Penalize top 10 holdings concentration
            top_10_pct = df_sorted.head(10)['pct'].sum()
            concentration_penalty = max(0, top_10_pct - 50)  # 50% is acceptable for top 10
            
            # Penalize any single holding >10%
            holdings_over_10 = df[df['pct'] > 10]
            single_stock_penalty = len(holdings_over_10) * 5  # -5 per holding over 10%
            
            # Penalize sector concentration >25%
            sector_allocation = PortfolioAnalyzer.compute_sector_allocation(holdings)
            sector_penalty = sum(max(0, pct - 25) * 0.5 for pct in sector_allocation.values())
            
            score = 100 - concentration_penalty - single_stock_penalty - sector_penalty
            return max(0, min(100, int(score)))
            
        except Exception as e:
            logger.error(f"Error computing diversification score: {e}")
            return 0

    @staticmethod
    def identify_concentration_risks(holdings: List[Dict]) -> List[Dict]:
        """
        Identify holdings that present concentration risk.
        Returns list of holdings with >10% concentration.
        """
        try:
            if not holdings:
                return []
            
            df = pd.DataFrame(holdings)
            df['value'] = df['quantity'] * df['price']
            
            total_value = df['value'].sum()
            if total_value <= 0:
                return []
            
            df['pct'] = (df['value'] / total_value) * 100
            
            risks = []
            for _, row in df[df['pct'] > 10].iterrows():
                risks.append({
                    'ticker': row['ticker'],
                    'concentration_pct': round(row['pct'], 2),
                    'value': round(row['value'], 2),
                    'severity': 'high' if row['pct'] > 20 else 'medium',
                    'issue': f"{row['ticker']} represents {round(row['pct'], 1)}% of portfolio (>10% threshold)"
                })
            
            return sorted(risks, key=lambda x: x['concentration_pct'], reverse=True)
        except Exception as e:
            logger.error(f"Error identifying concentration risks: {e}")
            return []

    @staticmethod
    def identify_sector_concentration_risks(holdings: List[Dict]) -> List[Dict]:
        """
        Identify sectors that present concentration risk.
        Returns sectors with >25% concentration.
        """
        try:
            sector_allocation = PortfolioAnalyzer.compute_sector_allocation(holdings)
            
            risks = []
            for sector, pct in sector_allocation.items():
                if pct > 25:
                    risks.append({
                        'sector': sector,
                        'concentration_pct': pct,
                        'severity': 'high' if pct > 50 else 'medium',
                        'issue': f"{sector} sector represents {pct}% of portfolio (>25% threshold)"
                    })
            
            return sorted(risks, key=lambda x: x['concentration_pct'], reverse=True)
        except Exception as e:
            logger.error(f"Error identifying sector concentration risks: {e}")
            return []

    @staticmethod
    def analyze_portfolio(holdings: List[Dict]) -> Dict[str, Any]:
        """
        Comprehensive portfolio analysis.
        Returns all metrics needed for Stage 3.
        """
        try:
            asset_allocation = PortfolioAnalyzer.compute_asset_allocation(holdings)
            sector_allocation = PortfolioAnalyzer.compute_sector_allocation(holdings)
            diversification_score = PortfolioAnalyzer.compute_diversification_score(holdings)
            concentration_risks = PortfolioAnalyzer.identify_concentration_risks(holdings)
            sector_risks = PortfolioAnalyzer.identify_sector_concentration_risks(holdings)
            
            # Compute total portfolio value
            df = pd.DataFrame(holdings)
            df['value'] = df['quantity'] * df['price']
            total_value = df['value'].sum()
            
            return {
                'total_value': round(total_value, 2),
                'holdings_count': len(holdings),
                'unique_sectors': len(sector_allocation),
                'asset_allocation': asset_allocation,
                'sector_allocation': sector_allocation,
                'diversification_score': diversification_score,
                'concentration_risks': concentration_risks,
                'sector_risks': sector_risks,
                'findings': {
                    'average_holding_size_pct': round(100 / len(holdings), 2),
                    'largest_holding_pct': round((df['value'].max() / total_value) * 100, 2),
                    'smallest_holding_pct': round((df['value'].min() / total_value) * 100, 2),
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return {
                'error': str(e),
                'holdings_count': len(holdings)
            }
