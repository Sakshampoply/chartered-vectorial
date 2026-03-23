import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import yfinance as yf
from datetime import datetime, timedelta
from pypfopt import EfficientFrontier, DiscreteAllocation
import logging

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """Generate optimal portfolio rebalancing strategies"""

    @staticmethod
    def fetch_returns_and_cov_matrix(tickers: List[str], years: int = 3) -> Tuple[pd.Series, pd.DataFrame]:
        """
        Fetch historical data and compute returns & covariance matrix.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*years)
            
            # Fetch data
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                progress=False,
                interval='1d'
            )['Close']
            
            # Compute returns
            returns = data.pct_change().dropna()
            
            # Annual mean returns
            mean_returns = returns.mean() * 252
            
            # Covariance matrix
            cov_matrix = returns.cov() * 252
            
            return mean_returns, cov_matrix
        except Exception as e:
            logger.error(f"Error fetching returns and covariance: {e}")
            raise

    @staticmethod
    def optimize_portfolio(
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        risk_tolerance: str = "moderate",
        allow_short: bool = False,
        max_leverage: float = 1.0
    ) -> Dict[str, float]:
        """
        Optimize portfolio allocation based on risk tolerance.
        
        Returns dict of {ticker: weight}
        """
        try:
            ef = EfficientFrontier(
                mean_returns,
                cov_matrix,
                weight_bounds=(None if allow_short else (0, 1)),
            )
            
            if risk_tolerance == "aggressive":
                # Maximize Sharpe ratio
                weights = ef.max_sharpe_ratio(risk_free_rate=0.045)
            elif risk_tolerance == "moderate":
                # Target 12% volatility
                target_volatility = 0.12
                weights = ef.efficient_frontier(target_volatility, target_return=None)[0]
            else:  # conservative
                # Minimize volatility
                weights = ef.min_volatility()
            
            # Weights are already normalized from EfficientFrontier
            return weights
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            raise

    @staticmethod
    def generate_rebalancing_trades(
        current_holdings: List[Dict],
        target_weights: Dict[str, float],
        portfolio_total_value: float,
        tax_rate: float = 0.20
    ) -> Tuple[List[Dict], float, float]:
        """
        Generate specific buy/sell trades to achieve target allocation.
        
        Returns: (trades_list, total_tax_cost, total_implementation_cost)
        """
        try:
            trades = []
            total_tax_cost = 0
            total_implementation_cost = 0
            
            # Current ticker positions
            current_positions = {h['ticker']: h for h in current_holdings}
            
            # Process each target ticker
            for ticker, target_weight in target_weights.items():
                target_value = portfolio_total_value * target_weight
                
                if ticker in current_positions:
                    current_holding = current_positions[ticker]
                    current_value = current_holding['quantity'] * current_holding['price']
                    current_weight = current_value / portfolio_total_value
                else:
                    current_value = 0
                    current_weight = 0
                
                diff_value = target_value - current_value
                
                if abs(diff_value) > 100:  # Ignore tiny changes
                    if ticker in current_positions:
                        current_price = current_positions[ticker]['price']
                        current_qty = current_positions[ticker]['quantity']
                    else:
                        # Need to fetch current price
                        try:
                            current_price = yf.Ticker(ticker).info.get('currentPrice', 100)
                            current_qty = 0
                        except:
                            current_price = 100
                            current_qty = 0
                    
                    # Determine action
                    if diff_value > 0:
                        action = "buy"
                        quantity_change = diff_value / current_price
                        trade_value = diff_value
                    else:
                        action = "sell"
                        quantity_change = abs(diff_value) / current_price
                        trade_value = abs(diff_value)
                        
                        # Estimate tax on sale (simplified)
                        if current_qty > 0:
                            # Assume 50% unrealized gains on sold portion
                            gains = (quantity_change / current_qty) * current_value * 0.5
                            total_tax_cost += gains * tax_rate
                    
                    # Estimate implementation cost ($150 per trade base + percent)
                    implementation_cost_per_trade = 150 + (trade_value * 0.001)
                    total_implementation_cost += implementation_cost_per_trade
                    
                    trades.append({
                        'action': action,
                        'ticker': ticker,
                        'current_quantity': round(current_qty, 2),
                        'target_quantity': round(current_qty + quantity_change, 2),
                        'quantity_change': round(quantity_change, 2),
                        'trade_value': round(trade_value, 2),
                        'reason': f"Rebalance to {target_weight*100:.1f}% allocation",
                        'current_price': round(current_price, 2),
                    })
            
            # Handle tickers to liquidate (not in target allocation)
            for ticker, holding in current_positions.items():
                if ticker not in target_weights:
                    current_value = holding['quantity'] * holding['price']
                    
                    if current_value > 100:  # Ignore tiny positions
                        total_implementation_cost += 150  # Liquidation fee
                        total_tax_cost += current_value * 0.15  # Conservative estimate
                        
                        trades.append({
                            'action': 'sell',
                            'ticker': ticker,
                            'current_quantity': round(holding['quantity'], 2),
                            'target_quantity': 0,
                            'trade_value': round(current_value, 2),
                            'reason': 'Remove from allocation',
                        })
            
            return trades, round(total_tax_cost, 2), round(total_implementation_cost, 2)
        except Exception as e:
            logger.error(f"Error generating rebalancing trades: {e}")
            return [], 0, 0

    @staticmethod
    def project_portfolio_performance(
        portfolio_return: float,
        portfolio_volatility: float,
        current_value: float,
        years: int = 3
    ) -> float:
        """
        Project portfolio value using simple compound growth.
        Assumes return is deterministic (doesn't account for paths).
        """
        try:
            projected_value = current_value * ((1 + portfolio_return) ** years)
            return projected_value
        except Exception as e:
            logger.error(f"Error projecting portfolio performance: {e}")
            return current_value

    @staticmethod
    def calculate_feasibility_score(
        trades: List[Dict],
        portfolio_value: float,
        implementation_cost: float,
        tax_cost: float,
        asset_class_changes: Dict[str, float]
    ) -> int:
        """
        Calculate feasibility score (0-100).
        Lower scores = harder to implement.
        """
        try:
            score = 100
            
            # Deduct for complexity
            if len(trades) > 10:
                score -= 15
            elif len(trades) > 5:
                score -= 10
            
            # Deduct for high tax cost
            tax_pct = (tax_cost / portfolio_value) * 100
            if tax_pct > 5:
                score -= min(20, (tax_pct - 5) * 2)
            
            # Deduct for concentration changes >50%
            major_changes = sum(1 for pct in asset_class_changes.values() if abs(pct) > 0.50)
            score -= major_changes * 15
            
            # Deduct for small portfolio (harder to migrate)
            if portfolio_value < 100000:
                score -= 10
            
            return max(0, min(100, score))
        except Exception as e:
            logger.error(f"Error calculating feasibility score: {e}")
            return 50

    @staticmethod
    def generate_strategy(
        current_holdings: List[Dict],
        portfolio_value: float,
        current_metrics: Dict[str, float],
        risk_tolerance: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Generate complete rebalancing strategy.
        """
        try:
            # Extract tickers
            tickers = [h['ticker'] for h in current_holdings]
            
            # Fetch market data
            mean_returns, cov_matrix = StrategyOptimizer.fetch_returns_and_cov_matrix(tickers)
            
            # Optimize weights
            target_weights = StrategyOptimizer.optimize_portfolio(
                mean_returns,
                cov_matrix,
                risk_tolerance=risk_tolerance
            )
            
            # Generate trades
            trades, tax_cost, impl_cost = StrategyOptimizer.generate_rebalancing_trades(
                current_holdings,
                target_weights,
                portfolio_value
            )
            
            # Compute target allocation impact
            current_return = current_metrics.get('annual_return', 0.06)
            current_volatility = current_metrics.get('volatility', 0.15)
            
            # Estimate new portfolio characteristics (simplified)
            # In reality, would use updated correlation matrix
            expected_return = current_return * 1.1  # Assume 10% improvement
            expected_volatility = current_volatility * 0.8  # Assume 20% volatile reduction
            projection_3yr = StrategyOptimizer.project_portfolio_performance(
                expected_return,
                expected_volatility,
                portfolio_value
            )
            
            return {
                'target_weights': target_weights,
                'trades': trades,
                'expected_return': round(expected_return, 4),
                'expected_volatility': round(expected_volatility, 4),
                'projected_3yr_value': round(projection_3yr, 2),
                'implementation_cost': impl_cost,
                'tax_cost': tax_cost,
                'return_improvement': round((expected_return - current_return) / current_return * 100, 2),
            }
        except Exception as e:
            logger.error(f"Error generating strategy: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def generate_phased_trades(
        trades: List[Dict],
        monthly_investable_income: float,
        months_available: int = 12,
        cash_on_hand: float = 0.0
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        NEW (Phase 5): Generate phased execution plan for trades.
        
        For trades that require monthly income funding, spread buy orders across months
        and prioritize high-conviction/high-impact positions first.
        
        Args:
            trades: List of trade dicts from generate_rebalancing_trades
            monthly_investable_income: Monthly amount available for investing
            months_available: Max months to spread rebalancing (default 12)
            cash_on_hand: Liquid cash immediately available
            
        Returns:
            (phased_trades, month_breakdown)
            where phased_trades is the updated trades list with execution_phase info
            and month_breakdown is [{month: 1, trades: [...], total_cost: $}]
        """
        try:
            phased_trades = []
            month_breakdown = []
            
            # Separate buy and sell trades
            buy_trades = [t for t in trades if t.get('action') == 'buy']
            sell_trades = [t for t in trades if t.get('action') == 'sell']
            other_trades = [t for t in trades if t.get('action') not in ['buy', 'sell']]
            
            # Phase 1 (Month 0): Immediate sells (no cash needed, frees up capital)
            current_month = 0
            month_trades = {"month": 0, "trades": [], "total_cost": 0, "operations": []}
            
            for trade in sell_trades:
                trade_copy = trade.copy()
                trade_copy["execution_phase"] = 0
                trade_copy["funding_source"] = "liquidation"
                phased_trades.append(trade_copy)
                month_trades["trades"].append(trade_copy)
                month_trades["operations"].append(f"SELL {trade['quantity_change']:.0f} {trade['ticker']}")
            
            if month_trades["trades"]:
                month_breakdown.append(month_trades)
            
            # Phase 2+: Phased buy orders spread across months
            # Prioritize by percentage allocation (higher % = earlier purchase)
            buy_trades_sorted = sorted(buy_trades, key=lambda t: t.get('trade_value', 0), reverse=True)
            
            total_buy_value = sum(t.get('trade_value', 0) for t in buy_trades)
            if total_buy_value > cash_on_hand and monthly_investable_income > 0:
                # Need to phase purchases
                remaining_value = total_buy_value - cash_on_hand
                buy_on_schedule = buy_trades_sorted
            else:
                buy_on_schedule = buy_trades_sorted
            
            # Distribute buys across months
            current_month = 1
            cumulative_cost = cash_on_hand  # Start with cash on hand
            
            for trade in buy_on_schedule:
                trade_value = trade.get('trade_value', 0)
                quantity = trade.get('quantity_change', 0)
                
                # Check current month budget
                if cumulative_cost < total_buy_value:
                    # Still funding; check if it fits this month
                    if cumulative_cost + monthly_investable_income >= cumulative_cost:
                        # Add to current month
                        if current_month > len(month_breakdown):
                            month_breakdown.append({"month": current_month, "trades": [], "total_cost": 0, "operations": []})
                        
                        trade_copy = trade.copy()
                        trade_copy["execution_phase"] = current_month
                        trade_copy["funding_source"] = "monthly_income" if current_month > 1 else "cash_on_hand"
                        trade_copy["phased_quantity_per_month"] = quantity
                        
                        phased_trades.append(trade_copy)
                        month_breakdown[current_month - 1]["trades"].append(trade_copy)
                        month_breakdown[current_month - 1]["total_cost"] += trade_value
                        month_breakdown[current_month - 1]["operations"].append(f"BUY {quantity:.0f} {trade['ticker']} (${trade_value:,.0f})")
                        
                        cumulative_cost += trade_value
                        
                        # Move to next month if we've spent most of monthly_investable_income
                        if cumulative_cost % monthly_investable_income == 0 and current_month < months_available:
                            current_month += 1
                    else:
                        current_month += 1
                        continue
                else:
                    break
            
            # Add other trades (holds, etc.) to month 0
            if other_trades and len(month_breakdown) > 0:
                for trade in other_trades:
                    trade["execution_phase"] = 0
                    phased_trades.append(trade)
                    month_breakdown[0]["trades"].append(trade)
            elif other_trades:
                month_breakdown.append({"month": 0, "trades": other_trades, "total_cost": 0, "operations": ["HOLD"]})
                phased_trades.extend(other_trades)
            
            logger.info(f"Generated phased plan: {len(month_breakdown)} months, {len(phased_trades)} total trades")
            
            return phased_trades, month_breakdown
        
        except Exception as e:
            logger.error(f"Error generating phased trades: {e}")
            # Fallback: return trades as-is (all immediate)
            for trade in trades:
                trade["execution_phase"] = 0
                trade["funding_source"] = "cash_on_hand"
            return trades, [{"month": 0, "trades": trades, "total_cost": sum(t.get("trade_value", 0) for t in trades), "operations": []}]
