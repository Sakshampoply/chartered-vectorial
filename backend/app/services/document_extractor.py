"""
Document Extractor Service

Handles extraction of holdings and account data from financial documents (PDFs).

Extraction pipeline:
1. pdfplumber - Fast table extraction from structured PDFs
2. unstructured - Binary document parsing for complex layouts
3. LLM fallback - Use Claude for unstructured document interpretation
4. yfinance validation - Verify extracted tickers are real
"""

import pdfplumber
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json

from app.services.llm_wrapper import LLMWrapper
from app.agents.prompts.document_intelligence import (
    DOCUMENT_PARSING_SYSTEM_PROMPT,
    FALLBACK_EXTRACTION_PROMPT,
    HOLDINGS_EXTRACTION_SCHEMA
)

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extract holdings and account data from portfolio documents"""
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None):
        """
        Initialize extractor
        
        Args:
            llm_wrapper: LLMWrapper instance for fallback extraction
                        Creates new instance if None
        """
        self.llm = llm_wrapper or LLMWrapper(model_name="openai/gpt-oss-120b")
        self.extraction_method = None
        self.confidence = 0.0
    
    async def extract(self, file_path: str, document_type: str = "portfolio_statement") -> Dict[str, Any]:
        """
        Extract holdings from document
        
        Args:
            file_path: Path to PDF file
            document_type: Type of document ("portfolio_statement", "account_summary", etc)
            
        Returns:
            {
                "status": "success" | "partial" | "error",
                "extracted_holdings": [{"ticker": str, "shares": float, "price": float}],
                "account_summary": {
                    "total_value": float,
                    "total_value_from_document": bool,
                    "cash": float,
                    "confidence": float,
                    "parsing_notes": str
                },
                "extraction_confidence": 0.0-1.0,
                "extraction_method": "llm" | "pdfplumber",
                "validation_errors": [str],
                "requires_manual_review": bool,
                "raw_text": str (for debugging)
            }
        """
        result = {
            "status": "error",
            "extracted_holdings": [],
            "account_summary": {
                "total_value": None,
                "total_value_from_document": False,
                "cash": 0,
                "confidence": 0.0,
                "parsing_notes": ""
            },
            "extraction_confidence": 0.0,
            "extraction_method": None,
            "validation_errors": [],
            "requires_manual_review": False,
            "raw_text": ""
        }
        
        try:
            if not Path(file_path).exists():
                result["validation_errors"].append(f"File not found: {file_path}")
                return result
            
            logger.info(f"Starting extraction from {file_path}")
            
            # Extract raw text first
            raw_text = ""
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        raw_text += page.extract_text() + "\n"
            except Exception as e:
                logger.warning(f"Could not extract raw text from PDF: {e}")
            
            # Try LLM extraction first (primary method)
            logger.info("Using LLM for document extraction (primary method)")
            holdings, summary = await self._extract_with_llm_fallback(file_path, raw_text, document_type)
            
            if holdings and len(holdings) > 0:
                self.extraction_method = "llm"
                self.confidence = 0.75  # Good confidence for LLM extraction
                result["extracted_holdings"] = holdings
                result["account_summary"] = summary
                result["extraction_method"] = "llm"
                result["extraction_confidence"] = 0.75
                result["raw_text"] = raw_text
                result["status"] = "success"
                
                logger.info(f"Successfully extracted {len(holdings)} holdings via LLM with total_value_from_document={summary.get('total_value_from_document', False)}")
                
            else:
                # Fallback to pdfplumber if LLM fails
                logger.info("LLM extraction returned no holdings, trying pdfplumber fallback")
                
                holdings, summary, raw_text = await self._extract_with_pdfplumber(file_path)
                
                if holdings and len(holdings) > 0:
                    self.extraction_method = "pdfplumber"
                    self.confidence = 0.85  # Higher confidence for structured tables
                    result["extracted_holdings"] = holdings
                    # pdfplumber fallback doesn't extract from document, it calculates
                    result["account_summary"]["total_value_from_document"] = False
                    result["account_summary"].update(summary)
                    result["extraction_method"] = "pdfplumber"
                    result["extraction_confidence"] = 0.85
                    result["raw_text"] = raw_text
                    result["status"] = "success"
                    
                    logger.info(f"Successfully extracted {len(holdings)} holdings via pdfplumber fallback")
                else:
                    result["status"] = "error"
                    result["validation_errors"].append("Could not extract holdings from document")
                    result["requires_manual_review"] = True
                    
                    logger.error("Failed to extract holdings from document")
            
            # Validate extracted holdings
            if result["extracted_holdings"]:
                validation_errors = self._validate_holdings(result["extracted_holdings"])
                result["validation_errors"].extend(validation_errors)
                
                if validation_errors:
                    result["requires_manual_review"] = True
            
            return result
        
        except Exception as e:
            logger.error(f"Document extraction error: {str(e)}")
            result["status"] = "error"
            result["validation_errors"].append(f"Exception: {str(e)}")
            result["requires_manual_review"] = True
            return result
    
    async def _extract_with_pdfplumber(
        self, 
        file_path: str
    ) -> Tuple[List[Dict], Dict[str, Any], str]:
        """
        Extract holdings using pdfplumber (structured tables)
        
        Returns: (holdings_list, account_summary, raw_text)
        """
        holdings = []
        summary = {}
        raw_text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                logger.info(f"PDF has {len(pdf.pages)} pages")
                
                # Extract text from all pages
                for page in pdf.pages:
                    raw_text += page.extract_text() + "\n"
                
                logger.debug(f"Extracted raw text length: {len(raw_text)} characters")
                
                # Try to find tables on first page and subsequent pages
                total_tables_found = 0
                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    
                    if tables:
                        total_tables_found += len(tables)
                        logger.info(f"Found {len(tables)} tables on page {page_idx}")
                        
                        for table_idx, table in enumerate(tables):
                            # Try to parse table as holdings
                            extracted = self._parse_holdings_table(table)
                            if extracted:
                                logger.info(f"Extracted {len(extracted)} holdings from table {table_idx} on page {page_idx}")
                                holdings.extend(extracted)
                            else:
                                logger.debug(f"Table {table_idx} on page {page_idx} did not contain valid holdings")
                    else:
                        logger.debug(f"No tables found on page {page_idx}")
                
                logger.info(f"Total tables found across all pages: {total_tables_found}")
                logger.info(f"Total holdings extracted via pdfplumber: {len(holdings)}")
                
                # Extract account summary from text
                summary = self._extract_account_summary(raw_text)
        
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {str(e)}", exc_info=True)
        
        return holdings, summary, raw_text
    
    async def _extract_with_llm_fallback(
        self,
        file_path: str,
        raw_text: str,
        document_type: str
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Extract holdings using LLM (for unstructured documents)
        
        Returns: (holdings_list, account_summary_with_metadata)
        
        account_summary includes:
        - total_value: Total portfolio value
        - total_value_from_document: Whether total_value was explicitly stated in document
        - cash: Cash/money market balance
        - parsing_notes: Any notes from LLM about extraction
        """
        holdings = []
        summary = {}
        
        try:
            # Limit text to first 4000 chars for token efficiency
            text_sample = raw_text[:4000]
            
            # Use LLM to extract holdings
            prompt = f"""{FALLBACK_EXTRACTION_PROMPT}

Document Type: {document_type}
Document Sample:
{text_sample}

Please extract all holdings found in this document. Return valid JSON."""
            
            response = await self.llm.agenerate_json(
                prompt=prompt,
                output_schema=HOLDINGS_EXTRACTION_SCHEMA,
                system_prompt=DOCUMENT_PARSING_SYSTEM_PROMPT
            )
            
            if response and isinstance(response, dict):
                holdings = response.get("holdings", [])
                
                # Preserve all metadata from LLM response
                summary = {
                    "total_value": response.get("total_value"),
                    "total_value_from_document": response.get("total_value_from_document", False),
                    "cash": response.get("cash", 0),
                    "confidence": response.get("confidence", 0.75),
                    "parsing_notes": response.get("parsing_notes", "")
                }
                
                logger.info(f"LLM extracted {len(holdings)} holdings with total_value={summary.get('total_value')}, from_document={summary.get('total_value_from_document')}")
        
        except Exception as e:
            logger.error(f"LLM fallback extraction error: {str(e)}")
        
        return holdings, summary
    
    def _parse_holdings_table(self, table: List[List[str]]) -> List[Dict]:
        """
        Parse holdings from a PDF table
        
        Args:
            table: List of rows from pdfplumber.extract_tables()
            
        Returns:
            List of {"ticker": str, "shares": float, "price": float}
        """
        holdings = []
        
        if not table or len(table) < 2:
            logger.debug(f"Table too small: {len(table) if table else 0} rows")
            return holdings
        
        try:
            # Look for header row (might contain "Symbol", "Ticker", "Shares", "Price")
            header = table[0]
            header_lower = [str(h).lower() if h else "" for h in header]
            
            logger.debug(f"Table header: {header}")
            
            # Find column indices
            ticker_idx = self._find_column_index(header_lower, ["ticker", "symbol", "sec", "code"])
            shares_idx = self._find_column_index(header_lower, ["shares", "quantity", "qty", "units"])
            price_idx = self._find_column_index(header_lower, ["price", "unit price", "value"])
            
            logger.debug(f"Column indices - ticker: {ticker_idx}, shares: {shares_idx}, price: {price_idx}")
            
            if ticker_idx is None:
                logger.debug(f"Could not find ticker column in table header: {header}")
                return holdings
            
            # Parse data rows
            for row_idx, row in enumerate(table[1:], start=1):
                if not row or len(row) == 0:
                    continue
                
                try:
                    ticker = str(row[ticker_idx]).strip().upper() if ticker_idx < len(row) else None
                    
                    if not ticker or len(ticker) == 0:
                        logger.debug(f"Row {row_idx}: ticker is empty")
                        continue
                    
                    shares = None
                    if shares_idx is not None and shares_idx < len(row):
                        shares = self._parse_float(row[shares_idx])
                    
                    price = None
                    if price_idx is not None and price_idx < len(row):
                        price = self._parse_float(row[price_idx])
                    
                    logger.debug(f"Row {row_idx}: ticker={ticker}, shares={shares}, price={price}")
                    
                    # Add if we have at least ticker and shares
                    if ticker and shares is not None:
                        holdings.append({
                            "ticker": ticker,
                            "shares": shares,
                            "price": price or 0.0
                        })
                        logger.debug(f"Added holding: {ticker} x {shares} @ ${price}")
                    else:
                        logger.debug(f"Row {row_idx} skipped: missing shares ({shares is None})")
                    
                except Exception as e:
                    logger.debug(f"Error parsing table row {row_idx}: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Table parsing error: {str(e)}")
        
        return holdings
    
    def _find_column_index(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index by matching keywords"""
        for idx, header in enumerate(headers):
            for keyword in keywords:
                if keyword in header:
                    return idx
        return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """Safely parse float value from various formats"""
        if value is None:
            return None
        
        try:
            # Remove common currency symbols and commas
            text = str(value).strip()
            text = re.sub(r'[$,\s]', '', text)
            
            if not text:
                return None
            
            return float(text)
        except (ValueError, TypeError):
            return None
    
    def _extract_account_summary(self, text: str) -> Dict[str, Any]:
        """Extract account-level information from document text"""
        summary = {
            "account_type": None,
            "total_value": None,
            "cash": None,
            "date": None
        }
        
        try:
            # Look for total value patterns
            total_patterns = [
                r"Total\s+(?:Portfolio\s+)?Value[:\s]+\$?([\d,]+\.?\d*)",
                r"Total\s+Assets[:\s]+\$?([\d,]+\.?\d*)",
                r"Account\s+Value[:\s]+\$?([\d,]+\.?\d*)",
            ]
            
            for pattern in total_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    summary["total_value"] = self._parse_float(match.group(1))
                    break
            
            # Look for cash/available funds
            cash_patterns = [
                r"Cash\s+(?:Balance|Available)[:\s]+\$?([\d,]+\.?\d*)",
                r"Money\s+Market[:\s]+\$?([\d,]+\.?\d*)",
            ]
            
            for pattern in cash_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    summary["cash"] = self._parse_float(match.group(1))
                    break
            
            # Look for date
            date_pattern = r"(?:As\s+of|Statement\s+Date)[:\s]+(\d{1,2}/\d{1,2}/\d{4})"
            match = re.search(date_pattern, text, re.IGNORECASE)
            if match:
                summary["date"] = match.group(1)
            
            # Determine account type
            if "401" in text.upper():
                summary["account_type"] = "401k"
            elif "IRA" in text.upper():
                summary["account_type"] = "IRA"
            elif "BROKERAGE" in text.upper():
                summary["account_type"] = "Brokerage"
            
        except Exception as e:
            logger.debug(f"Error extracting account summary: {str(e)}")
        
        return summary
    
    def _validate_holdings(self, holdings: List[Dict]) -> List[str]:
        """
        Validate extracted holdings
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            # Try importing yfinance for validation
            try:
                import yfinance
                has_yfinance = True
            except ImportError:
                has_yfinance = False
                logger.debug("yfinance not available for ticker validation")
            
            for holding in holdings:
                ticker = holding.get("ticker", "").upper()
                shares = holding.get("shares")
                price = holding.get("price")
                
                # Validate ticker format
                if not ticker:
                    errors.append("Found holding with empty ticker")
                    continue
                
                if not re.match(r'^[A-Z0-9\.]{1,5}$', ticker):
                    errors.append(f"Invalid ticker format: {ticker}")
                    continue
                
                # Validate shares
                if shares is not None and shares <= 0:
                    errors.append(f"Invalid shares for {ticker}: {shares}")
                
                # Optional: validate ticker exists with yfinance
                if has_yfinance and ticker not in ["CASH", "MONEY_MARKET"]:
                    try:
                        info = yfinance.Ticker(ticker).info
                        if not info or "regularMarketPrice" not in info:
                            errors.append(f"Could not verify ticker: {ticker}")
                    except Exception as e:
                        logger.debug(f"yfinance validation failed for {ticker}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
        
        return errors
