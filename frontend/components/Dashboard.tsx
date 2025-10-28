'use client'

import { useState, useEffect } from 'react'
import TickerManager from './TickerManager'
import NewsAnalyzer from './NewsAnalyzer'
import styles from './Dashboard.module.css'

interface Ticker {
  id: string
  symbol: string
  addedAt: string
}

export default function Dashboard() {
  const [tickers, setTickers] = useState<Ticker[]>([])
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)

  // Load tickers from localStorage on mount
  useEffect(() => {
    const savedTickers = localStorage.getItem('qq-ai-tickers')
    if (savedTickers) {
      try {
        setTickers(JSON.parse(savedTickers))
      } catch (e) {
        console.error('Failed to load tickers:', e)
      }
    }
  }, [])

  // Save tickers to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('qq-ai-tickers', JSON.stringify(tickers))
  }, [tickers])

  const handleAddTicker = (symbol: string) => {
    const newTicker: Ticker = {
      id: Date.now().toString(),
      symbol: symbol.toUpperCase(),
      addedAt: new Date().toISOString(),
    }
    setTickers([...tickers, newTicker])
  }

  const handleRemoveTicker = (id: string) => {
    setTickers(tickers.filter(t => t.id !== id))
    if (selectedTicker === id) {
      setSelectedTicker(null)
    }
  }

  const handleSelectTicker = (id: string) => {
    setSelectedTicker(id)
  }

  const selectedTickerData = tickers.find(t => t.id === selectedTicker)

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.logo}>
          <svg className={styles.logoSvg} viewBox="0 0 360 150" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="cleanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{stopColor: '#667eea', stopOpacity: 1}} />
                <stop offset="100%" style={{stopColor: '#764ba2', stopOpacity: 1}} />
              </linearGradient>
            </defs>
            <ellipse cx="150" cy="65" rx="50" ry="25" fill="none" stroke="url(#cleanGradient)" strokeWidth="5" opacity="0.9" />
            <ellipse cx="210" cy="85" rx="50" ry="25" fill="none" stroke="url(#cleanGradient)" strokeWidth="5" opacity="0.9" />
            <ellipse cx="180" cy="75" rx="20" ry="12" fill="url(#cleanGradient)" opacity="0.25" />
          </svg>
          <h1 className={styles.logoText}>Q&Q.AI</h1>
          <p className={styles.logoDescription}>Quantitative & Qualitative AI Investment Analysis System</p>
        </div>
      </header>

      {/* Main Content */}
      <main className={styles.main}>
        {/* Ticker Manager Panel */}
        <div className={styles.panel}>
          <TickerManager
            tickers={tickers}
            selectedTicker={selectedTicker}
            onAddTicker={handleAddTicker}
            onRemoveTicker={handleRemoveTicker}
            onSelectTicker={handleSelectTicker}
          />
        </div>

        {/* News Analyzer Panel */}
        {selectedTickerData && (
          <div className={styles.panel}>
            <NewsAnalyzer ticker={selectedTickerData.symbol} />
          </div>
        )}

        {/* Empty State */}
        {!selectedTickerData && (
          <div className={styles.emptyState}>
            <h2>No Ticker Selected</h2>
            <p>Select a ticker from your dashboard to view news analysis and impact insights</p>
          </div>
        )}
      </main>
    </div>
  )
}
