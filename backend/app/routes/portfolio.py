from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, status
from sqlalchemy.orm import Session
from uuid import UUID
import os
import shutil
from app.database import get_db, settings
from app.models.client import Client, Portfolio, Holding, UploadedFile
from app.schemas.portfolio_schema import PortfolioResponse, HoldingResponse
from app.services.portfolio_parser import PortfolioParser

router = APIRouter(prefix="/api/clients", tags=["portfolio"])


@router.post("/{client_id}/upload")
async def upload_portfolio_file(
    client_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a portfolio document (PDF, CSV, or TXT)"""
    try:
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Validate file type - support PDF (Phase 1), CSV, and TXT
        allowed_types = {'application/pdf', 'text/csv', 'text/plain', 'application/vnd.ms-excel'}
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="File type not supported. Use PDF, CSV, or TXT")
        
        # Validate file size
        max_size = settings.max_upload_size_mb * 1024 * 1024
        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(status_code=413, detail=f"File too large (max {settings.max_upload_size_mb}MB)")
        
        # Create uploads folder if doesn't exist
        os.makedirs(settings.upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(settings.upload_folder, f"{client_id}_{file.filename}")
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Parse portfolio (async operation)
        holdings, parse_msg, metadata = await PortfolioParser.parse_portfolio_file(file_path)
        
        if not holdings:
            os.remove(file_path)  # Clean up failed upload
            raise HTTPException(status_code=400, detail=f"Could not parse file: {parse_msg}")
        
        # Validate and enrich holdings
        holdings, warnings = PortfolioParser.validate_and_enrich_holdings(holdings)
        
        # Create portfolio and holdings in database
        portfolio = Portfolio(client_id=client_id, total_value=0)
        db.add(portfolio)
        db.flush()  # Get portfolio ID
        
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
                portfolio_id=portfolio.id,
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
        
        db.commit()
        
        return {
            "success": True,
            "message": parse_msg,
            "holdings_count": len(holdings),
            "portfolio_value": round(total_value, 2),
            "portfolio_value_source": total_source,
            "calculated_value": round(calculated_total, 2),
            "warnings": warnings[:3] if warnings else [],
            "portfolio_id": str(portfolio.id),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{client_id}/portfolio", response_model=PortfolioResponse)
def get_portfolio(client_id: UUID, db: Session = Depends(get_db)):
    """Get client's portfolio"""
    portfolio = db.query(Portfolio).filter(Portfolio.client_id == client_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return portfolio


@router.get("/{client_id}/portfolio/holdings")
def get_holdings(client_id: UUID, db: Session = Depends(get_db)):
    """Get all holdings in client's portfolio"""
    portfolio = db.query(Portfolio).filter(Portfolio.client_id == client_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio.id).all()
    
    return {
        "portfolio_id": str(portfolio.id),
        "total_value": portfolio.total_value,
        "holdings_count": len(holdings),
        "holdings": [
            {
                "id": str(h.id),
                "ticker": h.ticker,
                "quantity": h.quantity,
                "price": h.price,
                "value": h.value,
                "asset_class": h.asset_class,
                "sector": h.sector,
            }
            for h in holdings
        ]
    }


@router.delete("/{client_id}/portfolio")
def delete_portfolio(client_id: UUID, db: Session = Depends(get_db)):
    """Delete client's portfolio"""
    portfolio = db.query(Portfolio).filter(Portfolio.client_id == client_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    try:
        db.delete(portfolio)
        db.commit()
        return {"success": True, "message": "Portfolio deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
