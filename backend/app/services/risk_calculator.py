import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RiskCalculator:
    """Calculate financial risk metrics using market data"""

    # S&P 500 ticker for benchmark
    BENCHMARK_TICKER = "^GSPC"
    
    @staticmethod
    def fetch_historical_data(ticker: str, years: int = 3) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for a security.
        Returns DataFrame with OHLCV data.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*years)
            
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                interval='1d'
            )
            
            if data.empty:
                logger.warning(f"No data found for {ticker}")
                return None
            
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None

    @staticmethod
    def compute_returns(prices: pd.Series) -> pd.Series:
        """
        Compute daily returns from price series.
        Formula: (today - yesterday) / yesterday
        """
        try:
            returns = prices.pct_change().dropna()
            return returns
        except Exception as e:
            logger.error(f"Error computing returns: {e}")
            return pd.Series()

    @staticmethod
    def compute_annual_return(returns: pd.Series) -> float:
        """
        Compute annualized return.
        Formula: mean_daily_return * 252 trading days
        """
        try:
            if returns.empty:
                return 0.0
            
            mean_daily = returns.mean()
            annual_return = mean_daily * 252
            return float(annual_return)
        except Exception as e:
            logger.error(f"Error computing annual return: {e}")
            return 0.0

    @staticmethod
    def compute_volatility(returns: pd.Series) -> float:
        """
        Compute annualized volatility (standard deviation of returns).
        Formula: std(daily_returns) * sqrt(252)
        """
        try:
            if returns.empty:
                return 0.0
            
            daily_std = returns.std()
            annual_volatility = daily_std * np.sqrt(252)
            return float(annual_volatility)
        except Exception as e:
            logger.error(f"Error computing volatility: {e}")
            return 0.0

    @staticmethod
    def compute_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.045) -> float:
        """
        Compute Sharpe Ratio.
        Formula: (annual_return - risk_free_rate) / annual_volatility
        """
        try:
            annual_return = RiskCalculator.compute_annual_return(returns)
            volatility = RiskCalculator.compute_volatility(returns)
            
            if volatility == 0:
                return 0.0
            
            sharpe = (annual_return - risk_free_rate) / volatility
            return float(sharpe)
        except Exception as e:
            logger.error(f"Error computing Sharpe ratio: {e}")
            return 0.0

    @staticmethod
    def compute_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.045) -> float:
        """
        Compute Sortino Ratio (focuses on downside volatility).
        Formula: (annual_return - risk_free_rate) / downside_volatility
        """
        try:
            annual_return = RiskCalculator.compute_annual_return(returns)
            
            # Downside returns: negative returns only
            downside_returns = returns[returns < 0]
            if downside_returns.empty:
                return float(annual_return / 0.001)  # Avoid division by zero
            
            downside_std = downside_returns.std()
            downside_volatility = downside_std * np.sqrt(252)
            
            if downside_volatility == 0:
                return 0.0
            
            sortino = (annual_return - risk_free_rate) / downside_volatility
            return float(sortino)
        except Exception as e:
            logger.error(f"Error computing Sortino ratio: {e}")
            return 0.0

    @staticmethod
    def compute_beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """
        Compute Beta (market sensitivity).
        Formula: Cov(returns, benchmark) / Var(benchmark)
        """
        try:
            # Align series by date
            aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
            
            if len(aligned) < 2:
                return 1.0  # Default to market
            
            asset_returns = aligned.iloc[:, 0]
            market_returns = aligned.iloc[:, 1]
            
            covariance = np.cov(asset_returns, market_returns)[0][1]
            market_variance = np.var(market_returns)
            
            if market_variance == 0:
                return 1.0
            
            beta = covariance / market_variance
            return float(beta)
        except Exception as e:
            logger.error(f"Error computing beta: {e}")
            return 1.0

    @staticmethod
    def compute_max_drawdown(prices: pd.Series) -> float:
        """
        Compute maximum drawdown.
        Formula: (trough - peak) / peak for worst period
        """
        try:
            if prices.empty or len(prices) < 2:
                return 0.0
            
            # Compute running maximum
            running_max = prices.cummax()
            
            # Compute drawdown
            drawdown = (prices - running_max) / running_max
            
            # Get max drawdown (most negative)
            max_dd = drawdown.min()
            return float(max_dd)
        except Exception as e:
            logger.error(f"Error computing max drawdown: {e}")
            return 0.0

    @staticmethod
    def compute_portfolio_returns(holdings: List[Dict], price_history: Dict[str, pd.DataFrame]) -> pd.Series:
        """
        Compute portfolio daily returns from weighted holdings.
        """
        try:
            # Calculate weights
            df = pd.DataFrame(holdings)
            df['value'] = df['quantity'] * df['price']
            total_value = df['value'].sum()
            df['weight'] = df['value'] / total_value
            
            portfolio_returns = None
            
            for _, holding in df.iterrows():
                ticker = holding['ticker']
                weight = holding['weight']
                
                if ticker not in price_history:
                    continue
                
                price_data = price_history[ticker]
                holding_returns = RiskCalculator.compute_returns(price_data['Close'])
                
                if portfolio_returns is None:
                    portfolio_returns = weight * holding_returns
                else:
                    # Align by date
                    aligned = pd.concat([portfolio_returns, weight * holding_returns], axis=1).sum(axis=1)
                    portfolio_returns = aligned
            
            return portfolio_returns if portfolio_returns is not None else pd.Series()
        except Exception as e:
            logger.error(f"Error computing portfolio returns: {e}")
            return pd.Series()

    @staticmethod
    def compute_correlation_matrix(holdings: List[Dict], price_history: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """
        Compute correlation matrix between all holdings.
        """
        try:
            returns_dict = {}
            tickers = []
            
            for holding in holdings:
                ticker = holding['ticker']
                if ticker in price_history:
                    returns = RiskCalculator.compute_returns(price_history[ticker]['Close'])
                    if not returns.empty:
                        returns_dict[ticker] = returns
                        tickers.append(ticker)
            
            if len(tickers) < 2:
                return {}
            
            # Create DataFrame of returns
            returns_df = pd.DataFrame(returns_dict)
            correlation_matrix = returns_df.corr()
            
            # Convert to dict of dicts
            return correlation_matrix.to_dict()
        except Exception as e:
            logger.error(f"Error computing correlation matrix: {e}")
            return {}

    @staticmethod
    def analyze_portfolio_risk(holdings: List[Dict], risk_free_rate: float = 0.045) -> Dict[str, Any]:
        """
        Comprehensive portfolio risk analysis.
        """
        try:
            # Fetch historical data for all tickers
            price_history = {}
            tickers_list = list(set([h['ticker'] for h in holdings]))
            
            for ticker in tickers_list:
                data = RiskCalculator.fetch_historical_data(ticker)
                if data is not None:
                    price_history[ticker] = data
            
            if not price_history:
                logger.warning("No price data available")
                return {'error': 'No price data available for holdings'}
            
            # Fetch benchmark data
            benchmark_data = RiskCalculator.fetch_historical_data(RiskCalculator.BENCHMARK_TICKER)
            
            # Compute portfolio metrics
            portfolio_returns = RiskCalculator.compute_portfolio_returns(holdings, price_history)
            
            if portfolio_returns.empty:
                return {'error': 'Could not compute portfolio returns'}
            
            annual_return = RiskCalculator.compute_annual_return(portfolio_returns)
            volatility = RiskCalculator.compute_volatility(portfolio_returns)
            sharpe_ratio = RiskCalculator.compute_sharpe_ratio(portfolio_returns, risk_free_rate)
            sortino_ratio = RiskCalculator.compute_sortino_ratio(portfolio_returns, risk_free_rate)
            correlation_matrix = RiskCalculator.compute_correlation_matrix(holdings, price_history)
            
            # Compute beta if benchmark available
            beta = 1.0
            if benchmark_data is not None:
                benchmark_returns = RiskCalculator.compute_returns(benchmark_data['Close'])
                beta = RiskCalculator.compute_beta(portfolio_returns, benchmark_returns)
            
            # Compute max drawdown using cumulative returns
            cumulative_returns = (1 + portfolio_returns).cumprod()
            max_drawdown = RiskCalculator.compute_max_drawdown(cumulative_returns)
            
            # Assess risk alignment
            risk_assessment, alignment_issues = RiskCalculator.assess_risk_alignment(
                volatility, annual_return, risk_tolerance=None  # To be provided by client profile
            )
            
            return {
                'annual_return': round(annual_return, 4),
                'volatility': round(volatility, 4),
                'sharpe_ratio': round(sharpe_ratio, 3),
                'sortino_ratio': round(sortino_ratio, 3),
                'beta': round(beta, 3),
                'max_drawdown': round(max_drawdown, 4),
                'correlation_matrix': correlation_matrix,
                'data_points_count': len(portfolio_returns),
                'risk_assessment': risk_assessment,
                'alignment_issues': alignment_issues,
            }
        except Exception as e:
            logger.error(f"Error analyzing portfolio risk: {e}")
            return {'error': str(e)}

    @staticmethod
    def assess_risk_alignment(volatility: float, expected_return: float, risk_tolerance: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Assess if portfolio risk aligns with typical risk tolerance levels.
        
        Returns: (assessment, list_of_issues)
        """
        issues = []
        
        # Conservative target: volatility 8-12%, return 4-6%
        # Moderate target: volatility 12-18%, return 6-9%
        # Aggressive target: volatility 18-25%, return 9-12%
        
        if volatility < 0.08:
            issues.append("Portfolio volatility very low (<8%) - may not meet growth goals")
        elif volatility > 0.25:
            issues.append("Portfolio volatility very high (>25%) - consider more conservative allocation")
        
        if expected_return < 0.04:
            issues.append("Expected return very low (<4%) - verify asset quality")
        elif expected_return > 0.15:
            issues.append("Expected return very high (>15%) - verify assumptions")
        
        if volatility > 0 and expected_return > 0:
            risk_reward_ratio = expected_return / volatility
            if risk_reward_ratio < 0.2:
                issues.append("Risk-reward ratio low - portfolio may be taking too much risk for return")
        
        assessment = "balanced"
        if volatility < 0.12:
            assessment = "conservative"
        elif volatility > 0.18:
            assessment = "aggressive"
        
        return assessment, issues
