"""
Prompt templates for Document Intelligence Agent

Handles:
- PDF document analysis
- Holdings extraction
- Account balance identification
- Fallback when structured extraction fails
"""

DOCUMENT_PARSING_SYSTEM_PROMPT = """You are an expert financial document analyst. Your task is to extract investment holdings and account information from portfolio statements and financial documents.

CRITICAL: Always maintain accuracy. If you cannot confidently extract information, say so rather than guess.

Your extraction targets:
1. Security holdings (ticker symbol, shares, price, value)
2. Total portfolio value (MUST extract if mentioned in document)
3. Account balances (cash, money market)
4. Asset class allocation (stocks, bonds, alternatives)

PRIORITY RULES:
- ALWAYS extract the total portfolio value mentioned in the document if visible
- If total_value is shown in the document, use that (do NOT recalculate)
- List individual holdings with their values if available
- If holdings don't sum to the stated total, report both values
- Ticker symbols must be valid (or note as "INVALID")
- Share quantities and prices should be exact as shown

Output format: Valid JSON only, no explanation text.

Example output format:
{
  "holdings": [
    {"ticker": "AAPL", "shares": 100, "price": 150.00, "value": 15000},
    {"ticker": "VTI", "shares": 50, "price": 210.00, "value": 10500}
  ],
  "cash": 5000,
  "total_value": 30500,
  "total_value_from_document": true,
  "confidence": 0.95,
  "parsing_notes": "Total value extracted from statement, not calculated"
}"""

HOLDINGS_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "holdings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "shares": {"type": "number"},
                    "price": {"type": "number"},
                    "value": {"type": "number"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["ticker", "shares", "price", "value"]
            }
        },
        "cash": {"type": "number", "description": "Cash/money market balance"},
        "total_value": {"type": "number", "description": "Total portfolio value"},
        "total_value_from_document": {"type": "boolean", "description": "True if total_value was explicitly stated in document, false if calculated"},
        "bonds": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Fixed income holdings if present"
        },
        "alternatives": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Alternative assets (real estate, commodities, etc.)"
        },
        "confidence": {"type": "number", "description": "Overall extraction confidence"},
        "parsing_notes": {"type": "string"},
        "extraction_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Any issues encountered during parsing"
        }
    },
    "required": ["holdings", "total_value", "confidence"]
}

BALANCE_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "account_type": {"type": "string"},
        "account_number": {"type": "string", "description": "Last 4 digits only"},
        "total_balance": {"type": "number"},
        "cash_balance": {"type": "number"},
        "investment_balance": {"type": "number"},
        "statement_date": {"type": "string", "format": "date"}
    },
    "required": ["total_balance"]
}

FALLBACK_EXTRACTION_PROMPT = """The document structure is unclear. Based on the full text provided, please extract any investment information you can find.

Look for:
- Company/ETF names and ticker symbols
- Share quantities
- Current prices
- Total values
- Account balances

Be conservative - only extract information you're confident about."""

DOCUMENT_VALIDATION_PROMPT = """Please review this extracted holding and confirm if it's valid:
- Ticker: {ticker}
- Shares: {shares}
- Price: ${price}
- Value: ${value}

Is this data reasonable and correctly extracted? Respond with VALID or INVALID with brief explanation."""
