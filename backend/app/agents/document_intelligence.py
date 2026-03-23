import json

"""
Document Intelligence Agent

Orchestrates extraction of financial data from uploaded portfolio documents.
Integrates with LangGraph orchestrator for multi-document processing.

Flow:
1. Receive uploaded documents from state
2. For each document:
   - Extract holdings via DocumentExtractor
   - Validate extracted data
   - Update state with results
3. Flag documents requiring manual review
4. Return success/partial/error status
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.llm_wrapper import LLMWrapper
from app.agents.state import AnalysisState, AnalysisStateFactory

logger = logging.getLogger(__name__)


class DocumentIntelligenceAgent:
    """Agent for extracting holdings from portfolio documents"""
    
    def __init__(self, llm_wrapper: Optional[LLMWrapper] = None):
        """
        Initialize agent
        
        Args:
            llm_wrapper: LLMWrapper for fallback extraction
        """
        # Lazy import to avoid circular dependency
        from app.services.document_extractor import DocumentExtractor
        
        self.llm = llm_wrapper or LLMWrapper(model_name="openai/gpt-oss-120b")
        self.extractor = DocumentExtractor(llm_wrapper=self.llm)
    
    async def process_documents(self, state: AnalysisState) -> AnalysisState:
        """
        Process all uploaded documents in state
        
        Extracts holdings from each document, merges results,
        validates data, and updates state.
        
        Args:
            state: Current analysis state with uploaded_documents
            
        Returns:
            Updated state with extraction results
        """
        logger.info(
            f"Document Intelligence Agent starting for analysis {state['analysis_id']}"
        )
        
        state = AnalysisStateFactory.log_step(
            state,
            "document_intelligence_started",
            {"document_count": len(state.get("uploaded_documents", []))}
        )
        
        # Return unchanged if no documents
        if not state.get("uploaded_documents"):
            logger.info("No documents to process, skipping extraction")
            return state
        
        all_holdings = []
        extraction_results = []
        has_errors = False
        has_warnings = False
        all_manual_review = False
        
        # Process each document
        for doc in state["uploaded_documents"]:
            try:
                logger.info(f"Processing document: {doc.get('path')}")
                
                result = await self.extractor.extract(
                    file_path=doc["path"],
                    document_type=doc.get("type", "portfolio_statement")
                )
                
                extraction_results.append({
                    "document": doc["path"],
                    "status": result["status"],
                    "method": result["extraction_method"],
                    "confidence": result["extraction_confidence"],
                    "holdings_count": len(result["extracted_holdings"]),
                    "errors": result["validation_errors"],
                    "requires_review": result["requires_manual_review"]
                })
                
                # Merge holdings
                if result["extracted_holdings"]:
                    all_holdings.extend(result["extracted_holdings"])
                
                # Track issues
                if result["status"] == "error":
                    has_errors = True
                    state = AnalysisStateFactory.add_warning(
                        state,
                        f"Document extraction error for {doc['path']}: {', '.join(result['validation_errors'])}"
                    )
                
                if result["validation_errors"]:
                    has_warnings = True
                    for error in result["validation_errors"]:
                        state = AnalysisStateFactory.add_warning(state, error)
                
                if result["requires_manual_review"]:
                    all_manual_review = True
                    state = AnalysisStateFactory.add_warning(
                        state,
                        f"Document {doc['path']} requires manual review"
                    )
                
            except Exception as e:
                logger.error(f"Exception processing document {doc['path']}: {str(e)}")
                has_errors = True
                extraction_results.append({
                    "document": doc["path"],
                    "status": "error",
                    "error": str(e)
                })
                state = AnalysisStateFactory.add_error(
                    state,
                    "document_intelligence",
                    f"Failed to process {doc['path']}: {str(e)}"
                )
        
        # Update state with extraction results
        state["extracted_holdings"] = all_holdings
        state["extraction_results"] = extraction_results
        state["requires_manual_review"] = all_manual_review
        
        # Calculate aggregate metrics
        total_documents = len(state["uploaded_documents"])
        successful_documents = sum(
            1 for r in extraction_results if r.get("status") in ["success", "partial"]
        )
        
        # Set confidence based on extraction results
        if successful_documents > 0:
            avg_confidence = sum(
                r.get("confidence", 0.5) for r in extraction_results if r.get("confidence")
            ) / successful_documents
            state["document_extraction_confidence"] = avg_confidence
        
        # Determine extraction method (prefer pdfplumber)
        methods = [r.get("method") for r in extraction_results if r.get("method")]
        if "pdfplumber" in methods:
            state["document_extraction_method"] = "pdfplumber"
        elif methods:
            state["document_extraction_method"] = methods[0]
        
        # Log completion
        state = AnalysisStateFactory.log_step(
            state,
            "document_intelligence_complete",
            {
                "holdings_extracted": len(all_holdings),
                "documents_successful": successful_documents,
                "documents_total": total_documents,
                "has_errors": has_errors,
                "requires_manual_review": all_manual_review
            }
        )
        
        logger.info(
            f"Document Intelligence Agent complete: "
            f"{len(all_holdings)} holdings from {successful_documents}/{total_documents} documents"
        )
        
        return state
    
    async def extract_client_info(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Extract client info from supplemental documents to skip Q&A.
        """
        if not file_paths:
            return {}
            
        combined_text = ""
        for file_path in file_paths:
            try:
                if file_path.lower().endswith('.pdf'):
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                combined_text += text + "\n"
                else:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        combined_text += f.read() + "\n"
            except Exception as e:
                logger.warning(f"Failed to read {file_path} for client info: {e}")
                
        if not combined_text.strip():
            return {}
            
        # Call LLM
        from app.agents.prompts.document_intelligence import CLIENT_INFO_EXTRACTION_SYSTEM_PROMPT
        
        try:
            # Truncate to rough token limit if needed
            text_to_process = combined_text[:30000]
            
            response = await self.llm.generate(
                prompt=f"Extract client info from the following document text:\n\n{text_to_process}\n\nONLY return a JSON object.",
                system_prompt=CLIENT_INFO_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1
            )
            
            # Parse JSON
            text = response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            extracted = json.loads(text.strip())
            logger.info(f"Successfully extracted client info: {extracted}")
            return extracted
            
        except Exception as e:
            logger.error(f"Error during client info extraction: {e}")
            return {}

    async def validate_extracted_holdings(
        self,
        holdings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate extracted holdings for completeness and correctness
        
        Args:
            holdings: List of extracted holdings
            
        Returns:
            {
                "valid": bool,
                "total_holdings": int,
                "portfolio_value": float,
                "error_count": int,
                "errors": [str]
            }
        """
        errors = []
        total_value = 0.0
        valid_count = 0
        
        for holding in holdings:
            ticker = holding.get("ticker")
            shares = holding.get("shares", 0)
            price = holding.get("price", 0)
            
            # Validate required fields
            if not ticker:
                errors.append("Holding missing ticker")
                continue
            
            if shares <= 0:
                errors.append(f"Invalid shares for {ticker}: {shares}")
                continue
            
            # Calculate value
            value = shares * price if price > 0 else 0
            total_value += value
            valid_count += 1
        
        return {
            "valid": len(errors) == 0,
            "total_holdings": len(holdings),
            "valid_holdings": valid_count,
            "portfolio_value": total_value,
            "error_count": len(errors),
            "errors": errors
        }
    
    async def merge_multiple_documents(
        self,
        documents_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge holdings from multiple documents, handling duplicates
        
        Args:
            documents_results: List of extraction results from multiple documents
            
        Returns:
            Merged and deduplicated holdings list
        """
        merged = {}  # Key: ticker, Value: {shares, sources, prices}
        
        for doc_result in documents_results:
            if not doc_result.get("extracted_holdings"):
                continue
            
            for holding in doc_result["extracted_holdings"]:
                ticker = holding.get("ticker")
                shares = holding.get("shares", 0)
                price = holding.get("price")
                
                if ticker:
                    if ticker not in merged:
                        merged[ticker] = {
                            "shares": 0,
                            "prices": [],
                            "sources": []
                        }
                    
                    merged[ticker]["shares"] += shares
                    if price:
                        merged[ticker]["prices"].append(price)
                    merged[ticker]["sources"].append(doc_result.get("document"))
        
        # Convert back to list format
        result = []
        for ticker, data in merged.items():
            avg_price = (
                sum(data["prices"]) / len(data["prices"])
                if data["prices"]
                else 0.0
            )
            
            result.append({
                "ticker": ticker,
                "shares": data["shares"],
                "price": avg_price,
                "sources": data["sources"],
                "note": f"Combined from {len(data['sources'])} documents" if len(data["sources"]) > 1 else None
            })
        
        return result


# Convenience function for orchestrator integration
async def run_document_intelligence_agent(
    state: AnalysisState,
    llm_wrapper: Optional[LLMWrapper] = None
) -> AnalysisState:
    """
    Run document intelligence agent on analysis state
    
    Convenience function for use in LangGraph orchestrator nodes.
    
    Args:
        state: Current analysis state
        llm_wrapper: Optional LLM wrapper instance
        
    Returns:
        Updated state with document extraction results
    """
    agent = DocumentIntelligenceAgent(llm_wrapper=llm_wrapper)
    return await agent.process_documents(state)
