from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from app.database import engine, Base, settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models to ensure they're registered for SQLAlchemy
from app.models import *

# Import routes
from app.routes import clients, portfolio, analysis

# Create FastAPI app
app = FastAPI(
    title="Investment Advisory API",
    description="Multi-stage investment advisory platform for wealth management",
    version="1.0.0"
)

# CORS configuration
origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on app startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Include routers
app.include_router(clients.router)
app.include_router(portfolio.router)
app.include_router(analysis.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected",
        "services": ["portfolio_parser", "portfolio_analyzer", "risk_calculator", "strategy_optimizer"]
    }

# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", 8000))
    )
