# Chartered Vectorial - AI-Powered Investment Analysis Platform

An intelligent investment advisory platform that analyzes client portfolios and answers personalized financial questions using AI to generate actionable investment recommendations.

## Features

### Core Workflow

1. **Client Onboarding** - Enter client name and upload portfolio document (CSV, Excel, or PDF)
2. **Sequential Q&A** - Answer 7 personalized questions about investment goals and preferences
3. **AI Analysis** - Multi-agent system analyzes portfolio and generates recommendations
4. **Results Dashboard** - View comprehensive analysis across 5 tabs:
   - **Overview**: Key metrics and portfolio summary
   - **Portfolio**: Current holdings and allocation analysis
   - **Risk**: Risk assessment and volatility metrics
   - **Recommendations**: AI-powered actionable trades and strategies
   - **Explanations**: Deep dive rationale from financial experts

### Management Features

- **Client Browser**: Browse all clients and view their analysis history
- **Analysis Persistence**: All analyses saved to database for future reference
- **Responsive UI**: Modern Material Design interface with gradient styling

---

## Technology Stack

### Backend

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: OpenRouter API (Claude/GPT access)
- **Financial Analysis**: yfinance, numpy, pandas
- **Optimization**: PyPortfolioOpt

### Frontend

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI (MUI 5)
- **State Management**: React Context API
- **HTTP Client**: Fetch API

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 12+
- `pip` and `npm` package managers

### Step 1: Clone & Navigate

```bash
git clone <repository-url>
cd "Chartered Vectorial"
```

### Step 2: Environment Configuration

Create `.env` file in project root:

```bash
# Backend Database
DATABASE_URL=postgresql://user:password@localhost:5432/investmentadvisory

# Backend API
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
API_PORT=8000

# LLM API (OpenRouter)
OPENROUTER_API_KEY=your_openrouter_key_here

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

### Step 3: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database and tables
python3 << 'EOF'
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully")
EOF

# Start backend server (from backend directory)
uvicorn app.main:app --reload --port 8000
```

Backend will be available at: **http://localhost:8000**
API documentation: **http://localhost:8000/docs** (Swagger UI)

### Step 4: Database Setup (PostgreSQL)

**Option A: Using Docker** (Recommended)

```bash
docker run --name chartered-vectorial-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=investmentadvisory \
  -p 5432:5432 \
  -d postgres:15
```

**Option B: Manual Installation**

```bash
# On macOS (Homebrew)
brew install postgresql
brew services start postgresql
createdb -U postgres investmentadvisory

# On Linux (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb investmentadvisory

# On Windows (use PostgreSQL installer, then in psql:)
CREATE DATABASE investmentadvisory;
```

### Step 5: Frontend Setup

In a **new terminal window**:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

## Project Structure

```
Chartered Vectorial/
├── backend/
│   ├── app/
│   │   ├── models/              # Database models
│   │   │   ├── client.py        # Client & Analysis models
│   │   │   ├── risk.py          # Risk assessment model
│   │   │   └── recommendation.py # Recommendation model
│   │   ├── routes/              # API endpoints
│   │   │   ├── clients.py       # Client & analysis listing
│   │   │   ├── analysis.py      # Core analysis workflow
│   │   │   └── intake.py        # Q&A endpoints
│   │   ├── services/            # Core business logic
│   │   │   ├── portfolio_parser.py        # Parse portfolio files
│   │   │   ├── portfolio_analyzer.py      # Financial analysis
│   │   │   ├── analysis_orchestrator.py   # Coordinate analyses
│   │   │   └── llm_wrapper.py             # LLM integration
│   │   ├── schemas/             # API request/response models
│   │   ├── database.py          # Database configuration
│   │   └── main.py              # FastAPI app setup
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Example environment variables
│
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── InputForm/       # Initial onboarding form
│   │   │   ├── ChatInterface/   # Q&A chat interface
│   │   │   ├── ClientBrowser/   # Browse clients & history
│   │   │   └── Dashboard/       # Results dashboard
│   │   ├── contexts/            # React Context (state management)
│   │   │   └── AnalysisContext.tsx
│   │   ├── api/                 # API service layer
│   │   │   └── analysisApi.ts
│   │   ├── types/               # TypeScript interfaces
│   │   └── App.jsx              # Main app component
│   ├── package.json             # Node dependencies
│   ├── vite.config.ts           # Vite configuration
│   └── tsconfig.json            # TypeScript configuration
│
├── .env.example                 # Environment variables template
├── README.md                    # This file
└── CANDIDATE_ASSIGNMENT.md      # Assignment details
```

---

## API Endpoints

### Clients

```
GET    /api/clients                          # List all clients
POST   /api/clients/onboarding               # Create client + upload portfolio
GET    /api/clients/{client_id}/analyses     # Get analyses for a client
```

### Analysis

```
POST   /api/analysis/start                   # Initialize new analysis
POST   /api/analysis/{id}/info               # Get first question (POST to fetch)
POST   /api/analysis/{id}/ask                # Submit answer & get next question
POST   /api/analysis/{id}/execute            # Run full analysis
GET    /api/analysis/{id}/progress           # Check analysis progress
GET    /api/analysis/{id}/results            # Get completed analysis results
```

---

## Workflow Overview

### 1. Onboarding

- User enters client name
- Uploads portfolio document (CSV/Excel/PDF)
- Backend parses holdings and creates client profile

### 2. Q&A Phase

- User answers 7 sequential questions about investment goals
- Questions cover: risk tolerance, time horizon, income, tax situation, etc.
- Each answer builds client profile for analysis

### 3. Analysis Execution

- Backend triggers multi-stage analysis:
  - **Stage 1**: Parse portfolio → extract holdings
  - **Stage 2**: Analyze portfolio → calculate metrics (allocation, risk, etc.)
  - **Stage 3**: Generate recommendations → use LLM for strategy
- Results stored in database with UUID reference

### 4. Results Dashboard

- Display analysis across 5 tabs
- Show portfolio allocation, risk metrics, recommendations
- Allow browsing previous analyses

### 5. Client History

- Browse all clients in database
- Select client to view their analyses
- Click analysis to view detailed results

---

## Key Design Decisions

### 1. UUID-Based Analysis Tracking

All analyses get unique UUIDs for permanent reference and easy sharing.

### 2. Multi-Format Portfolio Parsing

Supports CSV, Excel, and PDF to accommodate various client document types.

### 3. Sequential Q&A Flow

Personalized questions generate better recommendations than static forms.

### 4. Deterministic Finance + LLM Advisory

- Financial calculations (volatility, Sharpe ratio, etc.) use pure Python
- Strategy explanations and recommendations come from LLM
- Ensures auditability and accuracy

### 5. Context API for State Management

Single source of truth for analysis state across all components prevents prop drilling.

---

## Testing the Application

### 1. Start All Services

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: PostgreSQL (if using Docker)
docker run --name chartered-vectorial-db ... (see setup above)
```

### 2. Open Application

Navigate to: **http://localhost:5173**

### 3. Test the Workflow

1. **Onboarding**
   - Enter a client name (e.g., "John Doe")
   - Upload a sample portfolio file
   - Submit to create client

2. **Q&A**
   - Answer the 7 questions about investment goals
   - Each answer submission fetches the next question
   - Continue until all questions answered

3. **Results**
   - View analysis results in 5-tab dashboard
   - Check portfolio allocation, risk metrics, recommendations

4. **Client Browser**
   - Click "Browse All Analyses" on home page
   - Select a client from the list
   - View all their analyses with dates and metrics
   - Click an analysis to view detailed results

---

## Troubleshooting

### Backend Issues

**Error: "Address already in use"**

- Port 8000 is occupied
- Solution: `lsof -i :8000` → find PID → `kill -9 <PID>`

**Error: "Cannot connect to database"**

- PostgreSQL not running
- Solution: Check DATABASE_URL in `.env` and verify PostgreSQL is running

**Error: "OpenRouter API key invalid"**

- Set OPENROUTER_API_KEY in `.env`
- Solution: Get key from https://openrouter.ai

### Frontend Issues

**Error: "Cannot POST to /api/analysis/..."**

- Backend not running
- Solution: Verify backend is running at http://localhost:8000

**Blank page on load**

- Check browser console for errors
- Solution: Clear cache and reload (Cmd+Shift+R)

**Module not found errors**

- Dependencies not installed
- Solution: Run `npm install` in frontend directory

---

## Development Workflow

### Adding a New Backend Endpoint

1. Create route in `backend/app/routes/`
2. Add SQLAlchemy model in `backend/app/models/` if needed
3. Add Pydantic schema in `backend/app/schemas/`
4. Register route in `backend/app/main.py`
5. Test with Swagger UI at `/docs`

### Adding a New Frontend Component

1. Create component in `src/components/`
2. Add TypeScript interface in `src/types/`
3. Add API method in `src/api/analysisApi.ts` if needed
4. Use context if component needs shared state
5. Add routing to `src/App.jsx` if it's a full page

### Database Migrations

Add new columns or tables:

```python
# In backend/
from app.database import Base, engine
from app.models import *  # Import all models

Base.metadata.create_all(bind=engine)  # Creates new tables
```

---

## Performance Metrics

- **Analysis execution**: ~15-30 seconds (depends on portfolio size)
- **API response**: <500ms (excluding analysis)
- **Frontend build**: ~1-2 seconds (Vite)
- **Page load**: <2 seconds

---

## Production Deployment

### Environment Variables for Production

```bash
DATABASE_URL=postgresql://<user>:<pass>@<prod-host>:5432/investmentadvisory
CORS_ORIGINS=https://yourdomain.com
API_PORT=8000
OPENROUTER_API_KEY=<your-key>
DEBUG=False
```

### Database

- Use AWS RDS, Azure Database, or managed PostgreSQL
- Enable automated backups
- Update DATABASE_URL to production host

### Backend

```bash
# Use Gunicorn for production
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### Frontend

```bash
# Build for production
npm run build

# Serve from ./dist via web server (Nginx, Apache, etc.)
```

### Security

- [ ] Set DEBUG=False
- [ ] Use HTTPS/SSL certificates
- [ ] Add authentication/authorization
- [ ] Implement rate limiting
- [ ] Enable CSRF protection
- [ ] Validate all inputs
- [ ] Use environment variables (no hardcoded secrets)

---

## Support & Contact

For issues or questions about setup:

1. Check `.env` configuration is correct
2. Verify PostgreSQL is running and accessible
3. Check backend logs: `uvicorn app.main:app --reload`
4. Check frontend console: Browser DevTools → Console tab
5. API documentation: http://localhost:8000/docs

---

**Version**: 1.0.0
**Last Updated**: March 2026
**Status**: Production-Ready
