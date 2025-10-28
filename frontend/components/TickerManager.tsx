'use client'

import { useState } from 'react'
import styles from './TickerManager.module.css'

interface Ticker {
  id: string
  symbol: string
  addedAt: string
}

interface TickerManagerProps {
  tickers: Ticker[]
  selectedTicker: string | null
  onAddTicker: (symbol: string) => void
  onRemoveTicker: (id: string) => void
  onSelectTicker: (id: string) => void
}

export default function TickerManager({
  tickers,
  selectedTicker,
  onAddTicker,
  onRemoveTicker,
  onSelectTicker,
}: TickerManagerProps) {
  const [inputValue, setInputValue] = useState('')
  const [error, setError] = useState('')

  const handleAdd = () => {
    const symbol = inputValue.trim().toUpperCase()
    
    // Validation
    if (!symbol) {
      setError('Please enter a ticker symbol')
      return
    }
    
    if (symbol.length > 5) {
      setError('Ticker symbol is too long')
      return
    }
    
    // Check if already exists
    if (tickers.some(t => t.symbol === symbol)) {
      setError('This ticker is already in your dashboard')
      return
    }
    
    onAddTicker(symbol)
    setInputValue('')
    setError('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAdd()
    }
  }

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Dashboard</h2>
      
      {/* Add Ticker Form */}
      <div className={styles.addForm}>
        <div className={styles.inputGroup}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value)
              setError('')
            }}
            onKeyPress={handleKeyPress}
            placeholder="Enter ticker (e.g., AAPL)"
            className={styles.input}
          />
          <button onClick={handleAdd} className={styles.addButton}>
            Add
          </button>
        </div>
        {error && <p className={styles.error}>{error}</p>}
      </div>

      {/* Ticker List */}
      <div className={styles.tickerList}>
        <h3 className={styles.listTitle}>Your Tickers ({tickers.length})</h3>
        
        {tickers.length === 0 ? (
          <p className={styles.emptyMessage}>No tickers yet. Add one above!</p>
        ) : (
          <div className={styles.tickers}>
            {tickers.map((ticker) => (
              <div
                key={ticker.id}
                className={`${styles.tickerCard} ${
                  selectedTicker === ticker.id ? styles.selected : ''
                }`}
                onClick={() => onSelectTicker(ticker.id)}
              >
                <div className={styles.tickerInfo}>
                  <span className={styles.symbol}>{ticker.symbol}</span>
                  <span className={styles.date}>
                    {new Date(ticker.addedAt).toLocaleDateString()}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onRemoveTicker(ticker.id)
                  }}
                  className={styles.removeButton}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
