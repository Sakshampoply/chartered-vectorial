"""
Consolidated client and onboarding routes

Endpoints:
POST   /api/clients/onboarding      - Unified onboarding (create client + upload portfolio)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
import logging
import os
from typing import Optional, List, Dict, Any

from app.database import get_db, settings
from app.models.client import Client, Portfolio, Holding, UploadedFile
from app.schemas.portfolio_schema import ClientResponse
from app.services.portfolio_parser import PortfolioParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.post("/onboarding")
async def onboarding(
    name: str = Form(...),
    file: UploadFile = File(...),
    supplemental_files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified onboarding endpoint: Create client and upload portfolio in one call.
    
    This consolidates the two-step process (client creation + portfolio upload) into
    a single endpoint for better UX.
    
    Request body (form-data):
    - name: Client name (string)
    - file: Portfolio document (PDF, CSV, or TXT)
    
    Returns: client_id, portfolio_id, holdings, and ready_for_analysis flag
    """
    try:
        # Step 1: Create client
        logger.info(f"[Onboarding] Creating client: {name}")
        
        client = Client(name=name)
        db.add(client)
        db.flush()  # Get client ID
        client_id = client.id
        
        # Step 2: Validate file type
        allowed_types = {'application/pdf', 'text/csv', 'text/plain', 'application/vnd.ms-excel'}
        if file.content_type not in allowed_types:
            db.rollback()
            raise HTTPException(
                status_code=400, 
                detail="File type not supported. Use PDF, CSV, or TXT"
            )
        
        # Step 3: Validate file size
        max_size = settings.max_upload_size_mb * 1024 * 1024
        contents = await file.read()
        if len(contents) > max_size:
            db.rollback()
            raise HTTPException(
                status_code=413, 
                detail=f"File too large (max {settings.max_upload_size_mb}MB)"
            )
        
        # Step 4: Save file
        os.makedirs(settings.upload_folder, exist_ok=True)
        file_path = os.path.join(settings.upload_folder, f"{client_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Step 5: Parse portfolio
        logger.info(f"[Onboarding] Parsing portfolio file: {file.filename}")
        holdings, parse_msg, metadata = await PortfolioParser.parse_portfolio_file(file_path)
        
        if not holdings:
            db.rollback()
            os.remove(file_path)
            raise HTTPException(
                status_code=400, 
                detail=f"Could not parse file: {parse_msg}"
            )
        
        # Step 6: Validate and enrich holdings
        holdings, warnings = PortfolioParser.validate_and_enrich_holdings(holdings)
        
        # Step 7: Create portfolio and holdings in database
        logger.info(f"[Onboarding] Creating portfolio with {len(holdings)} holdings")
        
        portfolio = Portfolio(client_id=client_id, total_value=0)
        db.add(portfolio)
        db.flush()  # Get portfolio ID
        portfolio_id = portfolio.id
        
        # Calculate holdings total
        calculated_total = 0
        for holding_data in holdings:
            holding_value = holding_data['quantity'] * holding_data['price']
            calculated_total += holding_value
        
        # Use extracted total_value if available and marked as from_document, otherwise use calculated
        if metadata.get('total_value_from_document') and metadata.get('total_value'):
            total_value = metadata['total_value']
            total_source = "document"
        else:
            total_value = calculated_total
            total_source = "calculated"
        
        # Add holdings to database
        for holding_data in holdings:
            holding_value = holding_data['quantity'] * holding_data['price']
            
            holding = Holding(
                portfolio_id=portfolio_id,
                ticker=holding_data['ticker'],
                quantity=holding_data['quantity'],
                price=holding_data['price'],
                value=holding_value,
                asset_class=holding_data.get('asset_class', 'Equity'),
                sector=holding_data.get('sector'),
            )
            db.add(holding)
        
        portfolio.total_value = total_value
        
        # Create uploaded file record
        uploaded_file = UploadedFile(
            client_id=client_id,
            filename=file.filename,
            file_path=file_path,
            file_type=file.filename.split('.')[-1].lower()
        )
        db.add(uploaded_file)
        
        # Handle supplemental files
        extracted_info = {}
        if supplemental_files:
            supp_paths = []
            for i, supp_file in enumerate(supplemental_files):
                if supp_file.filename:
                    # Save supplemental file
                    supp_path = os.path.join(settings.upload_folder, f"{client_id}_supp_{i}_{supp_file.filename}")
                    supp_contents = await supp_file.read()
                    if not supp_contents:
                        continue
                    with open(supp_path, "wb") as sf:
                        sf.write(supp_contents)
                    supp_paths.append(supp_path)
                    
                    # Create DB record for supplemental file
                    supp_record = UploadedFile(
                        client_id=client_id,
                        filename=supp_file.filename,
                        file_path=supp_path,
                        file_type=supp_file.filename.split('.')[-1].lower()
                    )
                    db.add(supp_record)
            
            # Extract info from supplemental documents
            if supp_paths:
                from app.agents.document_intelligence import DocumentIntelligenceAgent
                agent = DocumentIntelligenceAgent()
                extracted_info = await agent.extract_client_info(supp_paths)
                if extracted_info:
                    client.extracted_info = extracted_info
                    db.add(client)

        db.commit()
        
        logger.info(f"[Onboarding] Complete: client={client_id}, portfolio={portfolio_id}")
        
        return {
            "success": True,
            "message": f"Client {name} and portfolio successfully created",
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "holdings_count": len(holdings),
            "portfolio_value": round(total_value, 2),
            "portfolio_value_source": total_source,
            "warnings": warnings[:3] if warnings else [],
            "ready_for_analysis": True,
            "next_step": "POST /api/analysis/start with client_id and portfolio_id"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Onboarding] Error: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_clients(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get all clients in the system.
    
    Returns: List of clients with IDs and names
    """
    try:
        clients = db.query(Client).order_by(Client.created_at.desc()).all()
        return [
            {
                "client_id": str(client.id),
                "name": client.name,
                "created_at": client.created_at.isoformat() if client.created_at else None,
            }
            for client in clients
        ]
    except Exception as e:
        logger.error(f"[List Clients] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{client_id}/analyses")
async def get_client_analyses(
    client_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all analyses for a specific client.
    
    Returns: Client info and list of analyses
    """
    try:
        from app.models.client import AnalysisResult
        
        # Validate client exists
        try:
            client_uuid = UUID(client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid client ID format")
        
        client = db.query(Client).filter(Client.id == client_uuid).first()
        if not client:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
        
        # Get all analyses for this client
        analyses = db.query(AnalysisResult).filter(
            AnalysisResult.client_id == client_uuid
        ).order_by(AnalysisResult.created_at.desc()).all()
        
        return {
            "client_id": str(client.id),
            "client_name": client.name,
            "analyses_count": len(analyses),
            "analyses": [
                {
                    "analysis_id": str(analysis.id),
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                    "portfolio_value": analysis.portfolio_metrics_json.get("portfolio_value") if analysis.portfolio_metrics_json else None,
                    "risk_profile": analysis.risk_metrics_json.get("risk_level") if analysis.risk_metrics_json else analysis.risk_profile,
                }
                for analysis in analyses
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Get Client Analyses] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

