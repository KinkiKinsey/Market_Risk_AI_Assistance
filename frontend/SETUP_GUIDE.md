# Q&Q.AI Frontend Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start the Python API Server

The frontend requires the Python API server to be running. From the `frontend` directory:

```bash
python api_server.py
```

Or from the project root:

```bash
cd ..
python frontend/api_server.py
```

The API server should start on `http://localhost:8000`.

### 3. Start the Next.js Development Server

```bash
npm run dev
```

Or:

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## Features Overview

### Dashboard
- Add multiple tickers to your private watchlist
- Each ticker is saved in browser localStorage
- Click on a ticker to view its analysis

### News Analysis
- Automatically fetches up to 10 news items from the last 30 days
- Shows impact chains with sentiment analysis
- Green = Positive Impact
- Red = Negative Impact
- Gray = Neutral

### Treemap Visualization
- Interactive treemap showing macro and micro factors
- Click on any rectangle to flip the card
- Switch between Macro and Micro factors
- Hover to see quick details

### Custom News Input
- Click "+ Custom News" button
- Enter any market news text
- Get instant impact analysis
- Perfect for testing or analyzing breaking news

## API Integration

The frontend communicates with the Python backend for:

1. **News Fetching**: `POST /api/news`
   - Fetches news from FMP API
   - Limits to 10 items
   - Returns news, dates, and links

2. **Impact Analysis**: `POST /api/analyze-impact`
   - Analyzes news impact on financial metrics
   - Returns impact chains and treemap data
   - Uses your existing AI analysis engine

3. **Custom News**: `POST /api/custom-news-impact`
   - Analyzes custom news input
   - Returns impact analysis without fetching

## Environment Setup

### Python Requirements

Install these Python packages:

```bash
pip install fastapi uvicorn pydantic
```

### Node.js Requirements

All Node.js dependencies are in `package.json`:

- Next.js 14
- React 18
- TypeScript
- D3.js for treemap
- Axios for API calls

## Development

### Running in Development Mode

```bash
# Terminal 1: Python API
python api_server.py

# Terminal 2: Next.js Frontend
npm run dev
```

### Building for Production

```bash
npm run build
npm start
```

## Troubleshooting

### API Server Not Responding

1. Check if Python server is running on port 8000
2. Verify no firewall is blocking the connection
3. Check console for CORS errors

### News Not Loading

1. Verify FMP API key in `fmp_news_fetcher.py`
2. Check network tab for API errors
3. Ensure ticker symbol is valid

### Treemap Not Rendering

1. Check browser console for D3 errors
2. Verify data is being returned from API
3. Ensure D3 library is installed

## Customization

### Changing Colors

Edit `app/globals.css` to change the color scheme:
- `--accent-primary`: Main gradient color
- `--accent-secondary`: Secondary gradient color
- `--bg-primary`: Background color

### Modifying API Endpoints

Edit API calls in:
- `components/NewsAnalyzer.tsx`
- `components/Treemap.tsx`

### Adding New Features

1. Create new component in `components/`
2. Add styles in `components/Component.module.css`
3. Import in `components/Dashboard.tsx`

## Architecture

```
User Action → Component → API Call → Python Backend
                                   ↓
                            AI Analysis Engine
                                   ↓
                            Return Results → Display
```

## Next Steps

1. **Connect Real AI Engine**: Replace mock data in `api_server.py` with actual AI calls
2. **Add Authentication**: Implement user authentication for private dashboards
3. **Add More Visualizations**: Add charts, graphs, and other visualizations
4. **Optimize Performance**: Add caching, lazy loading, and performance optimizations
5. **Mobile Responsive**: Improve mobile layout and interactions

## Support

For questions or issues, please refer to the main Q&Q.AI documentation.
