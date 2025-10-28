# Q&Q.AI Frontend

A Next.js frontend for the Q&Q.AI Hedge Fund Intelligence Platform.

## Features

- 📊 **Private Dashboard**: Add and manage your watchlist of tickers
- 📰 **News Analysis**: View up to 10 news items per ticker with AI impact analysis
- 🗺️ **Treemap Visualization**: Interactive treemap showing macro and micro factors
- 🃏 **Card Flip Effect**: Click on treemap items to flip and see detailed impact information
- ✍️ **Custom News Input**: Analyze custom market news for immediate impact insights
- 🎨 **Modern UI**: Beautiful gradient design matching the Q&Q.AI brand

## Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (for API server)
- Backend API running on http://localhost:8000

### Installation

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start the Python API server:**
```bash
python api_server.py
```

3. **Start the Next.js development server:**
```bash
npm run dev
```

4. **Open your browser:**
Navigate to http://localhost:3000

## Usage

### Adding Tickers to Dashboard

1. Enter a ticker symbol (e.g., "AAPL") in the input field
2. Click "Add" or press Enter
3. Ticker will be saved to your private dashboard

### Analyzing News

1. Click on a ticker from your dashboard
2. News will be automatically fetched and analyzed
3. View impact analysis in the "News Impact" tab
4. Switch to "Treemap Analysis" to see visual factors

### Treemap Interaction

- Click on any rectangle to flip the card
- Hover to see quick information
- Switch between Macro and Micro factors using tabs
- Green = Positive Impact, Red = Negative Impact

### Custom News Input

1. Click "+ Custom News" button
2. Enter market news text
3. Click "Analyze Impact"
4. View results in the treemap

## Project Structure

```
frontend/
├── app/                    # Next.js 14 App Router
│   ├── page.tsx           # Main page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/             # React components
│   ├── Dashboard.tsx      # Main dashboard
│   ├── TickerManager.tsx  # Ticker management
│   ├── NewsAnalyzer.tsx   # News and impact analysis
│   ├── Treemap.tsx        # Treemap visualization
│   └── *.module.css       # Component styles
├── api_server.py          # Python FastAPI backend
├── package.json           # Dependencies
└── README.md             # This file
```

## API Endpoints

The frontend communicates with the Python backend on `http://localhost:8000`:

- `POST /api/news` - Fetch news for a ticker
- `POST /api/analyze-impact` - Analyze news impact
- `POST /api/custom-news-impact` - Analyze custom news

## Technologies

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **D3.js** - Data visualization (treemap)
- **Framer Motion** - Animations
- **Tailwind CSS** - Styling utilities
- **FastAPI** - Python backend API

## Data Persistence

Tickers are saved in browser localStorage under the key `qq-ai-tickers`.

## Notes

- The API server uses mock data for demo purposes
- In production, connect to your actual AI analysis backend
- All API calls are to the Python backend running on port 8000
- News is limited to 10 items per ticker

## License

© 2025 Q&Q.AI - Bridging Data Intelligence
