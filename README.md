# Q&Q.AI - Quantitative & Qualitative AI Investment Analysis System

A comprehensive hedge fund intelligence platform that combines quantitative analysis with qualitative AI insights to provide actionable investment intelligence.

## 🏗️ Project Structure

```
QandQ_AI/
├── backend/                      # Complete Python backend (FastAPI + Analysis Pipeline)
│   ├── api_server.py            # Main API server
│   ├── requirements.txt         # Python dependencies
│   ├── config.env               # Environment variables
│   ├── fmp_news_fetcher.py     # News fetching module
│   ├── hedge_fund_analyst_with_sentiment.py  # AI analysis engine
│   ├── shared_clients.py        # Shared Redis/DB clients
│   ├── New_Supervisor_Agent.ipynb  # Supervisor agent notebook
│   ├── Mid_Agent_Folder/       # Mid-level analysis agents
│   │   ├── Hedge_Fund_Brain.py # Main brain function
│   │   └── Data_Retrieval/     # Data retrieval modules
│   ├── Sub_Agent_Folder/       # Specialized sub-agents
│   │   ├── Earning_and_Future_Agent/
│   │   ├── Financial_Metrics_Agent/
│   │   ├── Macro_Analyst_Agent/
│   │   ├── Market_Expectation_Agent/
│   │   ├── Quant_Impact_Agent/
│   │   └── Sector_Analyst_Agent/
│   ├── data_source/            # Data sources (get_price, etc.)
│   └── Extra/                  # Additional utilities & notebooks
│
├── frontend/                    # Next.js frontend (UI only)
│   ├── app/                    # Next.js 14 App Router
│   ├── components/             # React components
│   ├── package.json            # Node.js dependencies
│   └── tsconfig.json           # TypeScript config
│
├── docker/                     # Docker deployment files
│   ├── backend.Dockerfile      # Backend container
│   ├── frontend.Dockerfile     # Frontend container
│   └── docker-compose.yml      # Multi-container setup
│
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **npm** or **yarn**
- **Redis** (for data caching)
- **API Keys** (FMP, OpenAI, etc.)

### Local Development

#### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables (if config.env doesn't exist)
# Edit config.env with your API keys (FMP, OpenAI, Redis, etc.)

# Run API server
python api_server.py
# Or using uvicorn:
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

Backend will run on: **http://localhost:8000**

#### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Run development server
npm run dev
```

Frontend will run on: **http://localhost:3000**

### Docker Deployment

```bash
# Build and run all services
cd docker
docker-compose up --build

# Or run in detached mode
docker-compose up -d

# Stop services
docker-compose down
```

## 📋 Features

### Core Functionality

- **📊 Private Dashboard**: Manage your ticker watchlist
- **📰 News Analysis**: AI-powered news impact analysis (up to 10 items per ticker)
- **🗺️ Treemap Visualization**: Interactive macro/micro factor analysis
- **🃏 Card Flip Interactions**: Detailed impact insights on click
- **✍️ Custom News Input**: Analyze any market news instantly
- **📈 Progress Tracking**: Real-time analysis progress updates

### AI Analysis

- **Qualitative Intelligence**: Brain and alpha insights
- **Quantitative Metrics**: Risk-reward calculations
- **Impact Chains**: News → Financial Metric → Reasoning
- **Sentiment Analysis**: Confidence scoring for predictions

## 🔌 API Endpoints

### Backend API (Port 8000)

- `GET /` - Health check
- `POST /api/news` - Fetch news for ticker
- `POST /api/analyze-impact` - Analyze news impact
- `POST /api/custom-news-impact` - Analyze custom news

### Example API Call

```bash
curl -X POST http://localhost:8000/api/news \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "days": 30}'
```

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Pandas** - Data manipulation
- **yfinance** - Stock data fetching
- **Redis** - Caching layer
- **LangChain** - AI agent framework

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **D3.js** - Data visualization (treemap)
- **CSS Modules** - Component-scoped styling

## 📁 Key Backend Modules

- `fmp_news_fetcher.py` - Fetches news from Financial Modeling Prep API
- `hedge_fund_analyst_with_sentiment.py` - AI analysis engine
- `Mid_Agent_Folder/` - High-level analysis agents
- `Sub_Agent_Folder/` - Specialized agent modules:
  - Earnings & Future Agent
  - Financial Metrics Agent
  - Macro Analyst Agent
  - Market Expectation Agent
  - Quant Impact Agent
  - Sector Analyst Agent

## 🔐 Environment Variables

Create a `config.env` file in the `backend/` directory:

```env
FMP_API_KEY=your_fmp_api_key
OPENAI_API_KEY=your_openai_key
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 📝 Development Notes

- Backend uses **real data only** - no mock data
- Frontend communicates via REST API to backend
- News is limited to 10 items per ticker
- All analysis results are cached in Redis

## 🐳 Docker Notes

- Backend runs on port 8000
- Frontend runs on port 3000
- Services communicate via Docker network
- Volume mounts for hot-reload in development

## 📄 License

© 2025 Q&Q.AI - Bridging Data Intelligence

## 🤝 Contributing

This is a private project. For questions or issues, contact the development team.

