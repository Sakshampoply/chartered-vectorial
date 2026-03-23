import csv
import re
import yfinance as yf
import asyncio
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from app.models.client import Holding, AssetClass
import logging

logger = logging.getLogger(__name__)

# Sector classifications (simplified)
SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology", "NVDA": "Technology",
    "JNJ": "Healthcare", "PFE": "Healthcare", "V": "Finance", "JPM": "Finance",
    "XOM": "Energy", "CVX": "Energy", "WMT": "Consumer", "PG": "Consumer",
    "BAC": "Finance", "GS": "Finance", "TSLA": "Technology", "META": "Technology",
    "BRK.B": "Finance", "AMZN": "Consumer", "NFLX": "Consumer",
    "AGG": "Fixed Income", "BND": "Fixed Income", "VBTLX": "Fixed Income",
    "VTI": "Equity", "VTSAX": "Equity", "SPLG": "Equity",
}

ASSET_CLASS_MAP = {
    "AGG": AssetClass.FIXED_INCOME, "BND": AssetClass.FIXED_INCOME, "VBTLX": AssetClass.FIXED_INCOME,
    "VTI": AssetClass.EQUITY, "VTSAX": AssetClass.EQUITY, "SPLG": AssetClass.EQUITY,
    "MMKT": AssetClass.CASH, "SPAXX": AssetClass.CASH,
}


class PortfolioParser:
    """Parse portfolio documents (CSV, TXT) and extract holdings"""

    @staticmethod
    def parse_csv(file_path: str) -> Tuple[List[Dict], str]:
        """
        Parse CSV file and extract holdings.
        Expected columns: Ticker, Quantity, Price, [Sector], [Asset Class]
        """
        try:
            holdings = []
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normalize column names
                    normalized_row = {k.lower().strip(): v for k, v in row.items()}
                    
                    ticker = normalized_row.get('ticker') or normalized_row.get('symbol')
                    quantity = normalized_row.get('quantity') or normalized_row.get('shares')
                    price = normalized_row.get('price') or normalized_row.get('current price')
                    
                    if not ticker or not quantity or not price:
                        logger.warning(f"Skipping incomplete row: {row}")
                        continue
                    
                    try:
                        holding = {
                            'ticker': ticker.upper().strip(),
                            'quantity': float(quantity),
                            'price': float(price),
                            'sector': normalized_row.get('sector'),
                            'asset_class': normalized_row.get('asset_class'),
                        }
                        holdings.append(holding)
                    except ValueError as e:
                        logger.warning(f"Error parsing row {row}: {e}")
                        continue
            
            if not holdings:
                return [], "No valid holdings found in CSV"
            
            return holdings, f"Successfully parsed {len(holdings)} holdings from CSV"
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            return [], f"Error parsing CSV: {str(e)}"

    @staticmethod
    def parse_text(file_path: str) -> Tuple[List[Dict], str]:
        """
        Parse plain text portfolio statement.
        Looks for patterns like: TICKER QUANTITY@PRICE or similar
        Falls back to LLM if pattern matching fails.
        """
        try:
            holdings = []
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Pattern matching for common formats
            # Pattern 1: TICKER QUANTITY @/at PRICE
            pattern1 = r'([A-Z]{1,5}\.?[A-Z]?)\s+(\d+\.?\d*)\s+@\s*\$?(\d+\.?\d*)'
            # Pattern 2: TICKER: QUANTITY shares @ $PRICE
            pattern2 = r'([A-Z]{1,5}\.?[A-Z]?):?\s+(\d+\.?\d*)\s+shares?\s+@\s*\$?(\d+\.?\d*)'
            
            matches = re.findall(pattern1, content, re.MULTILINE)
            if not matches:
                matches = re.findall(pattern2, content, re.MULTILINE)
            
            for match in matches:
                try:
                    holding = {
                        'ticker': match[0].upper().strip(),
                        'quantity': float(match[1]),
                        'price': float(match[2]),
                        'sector': None,
                        'asset_class': None,
                    }
                    holdings.append(holding)
                except ValueError:
                    continue
            
            if holdings:
                return holdings, f"Successfully parsed {len(holdings)} holdings from text"
            else:
                return [], "Could not parse holdings from text file (no matching patterns found)"
                
        except Exception as e:
            logger.error(f"Error parsing text: {e}")
            return [], f"Error parsing text: {str(e)}"

    @staticmethod
    async def parse_pdf(file_path: str) -> Tuple[List[Dict], str, Dict]:
        """
        Parse PDF portfolio statement using DocumentExtractor (Phase 1).
        Handles both structured tables and unstructured documents.
        Uses existing event loop instead of creating a new one.
        
        Returns: (holdings, message, metadata_dict)
        metadata_dict includes:
        - total_value: Extracted total portfolio value (if from_document=true)
        - total_value_from_document: Whether total_value was explicitly stated
        - extraction_method: "llm" or "pdfplumber"
        - extraction_confidence: Confidence score 0.0-1.0
        """
        try:
            from app.services.document_extractor import DocumentExtractor
            from app.agents.config import get_llm_config
            from app.services.llm_wrapper import LLMWrapper
            
            # Initialize extractor with LLM wrapper
            config = get_llm_config()
            llm_wrapper = LLMWrapper(config=config)
            extractor = DocumentExtractor(llm_wrapper=llm_wrapper)
            
            # Call async extraction directly (we're already in an async context)
            result = await extractor.extract(file_path, document_type="portfolio_statement")
            
            # Convert extracted holdings to portfolio format
            if result['status'] == 'error' or not result['extracted_holdings']:
                errors = result.get('validation_errors', [])
                error_msg = '; '.join(errors) if errors else "No holdings extracted from PDF"
                return [], f"Could not extract holdings from PDF: {error_msg}", {}
            
            holdings = []
            for holding_data in result['extracted_holdings']:
                holding = {
                    'ticker': holding_data.get('ticker', '').upper().strip(),
                    'quantity': float(holding_data.get('shares', 0)),
                    'price': float(holding_data.get('price', 0)),
                    'sector': None,
                    'asset_class': None,
                    'extraction_confidence': result.get('extraction_confidence', 0.5),
                    'extraction_method': result.get('extraction_method', 'unknown'),
                }
                if holding['ticker'] and holding['quantity'] > 0:
                    holdings.append(holding)
            
            if not holdings:
                return [], "No valid holdings found in PDF", {}
            
            # Extract metadata from account_summary
            account_summary = result.get('account_summary', {})
            metadata = {
                'total_value': account_summary.get('total_value'),
                'total_value_from_document': account_summary.get('total_value_from_document', False),
                'extraction_method': result.get('extraction_method', 'unknown'),
                'extraction_confidence': result.get('extraction_confidence', 0.5),
            }
            
            confidence = result.get('extraction_confidence', 0.5)
            method = result.get('extraction_method', 'unknown')
            msg = f"Successfully extracted {len(holdings)} holdings from PDF (method: {method}, confidence: {confidence:.0%})"
            
            logger.info(msg)
            return holdings, msg, metadata
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}", exc_info=True)
            return [], f"Error parsing PDF: {str(e)}", {}

    @staticmethod
    def validate_and_enrich_holdings(holdings: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Validate tickers exist and enrich with sector/asset class information.
        Uses yfinance to verify tickers.
        """
        validated = []
        warnings = []
        
        for holding in holdings:
            ticker = holding['ticker']
            
            try:
                # Try to fetch info from yfinance
                tick = yf.Ticker(ticker)
                info = tick.info
                
                # Enrich with sector and asset class if available
                if not holding.get('sector'):
                    holding['sector'] = info.get('sector', SECTOR_MAP.get(ticker))
                
                if not holding.get('asset_class'):
                    # Try to determine asset class
                    if 'AGG' in ticker or 'BND' in ticker or 'VBTLX' in ticker:
                        holding['asset_class'] = AssetClass.FIXED_INCOME
                    elif 'MMKT' in ticker or 'SPAXX' in ticker:
                        holding['asset_class'] = AssetClass.CASH
                    elif holding.get('sector') in ['Finance', 'Technology', 'Healthcare']:
                        holding['asset_class'] = AssetClass.EQUITY
                    else:
                        holding['asset_class'] = AssetClass.EQUITY  # Default
                
                validated.append(holding)
                
            except Exception as e:
                warnings.append(f"Could not validate ticker {ticker}: {str(e)}")
                # Still add it but mark as potentially invalid
                holding['asset_class'] = holding.get('asset_class', AssetClass.EQUITY)
                validated.append(holding)
        
        return validated, warnings

    @staticmethod
    async def parse_portfolio_file(file_path: str) -> Tuple[List[Dict], str, Dict]:
        """
        Main entry point for parsing portfolio files.
        Automatically detects format and parses accordingly.
        
        Supports:
        - PDF: Using Phase 1 DocumentExtractor (pdfplumber + LLM fallback)
        - CSV: Structured comma-separated values
        - TXT: Plain text with ticker/quantity/price patterns
        
        Returns: (holdings, message, metadata_dict)
        """
        metadata = {}
        
        # Determine file type
        if file_path.endswith('.pdf'):
            holdings, msg, metadata = await PortfolioParser.parse_pdf(file_path)
        elif file_path.endswith('.csv'):
            holdings, msg = PortfolioParser.parse_csv(file_path)
        elif file_path.endswith(('.txt', '.text')):
            holdings, msg = PortfolioParser.parse_text(file_path)
        else:
            return [], f"Unsupported file format: {file_path}", {}
        
        if not holdings:
            return [], msg, metadata
        
        # Validate and enrich
        validated, warnings = PortfolioParser.validate_and_enrich_holdings(holdings)
        
        if warnings:
            msg += f"\nWarnings: {'; '.join(warnings[:3])}"  # Limit to first 3 warnings
        
        return validated, msg, metadata
