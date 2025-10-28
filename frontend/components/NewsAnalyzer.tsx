'use client'

import React, { useState, useEffect } from 'react'
import axios from 'axios'
import Treemap from './Treemap'
import RealProgressBar from './RealProgressBar'
import styles from './NewsAnalyzer.module.css'

interface NewsItem {
  news: string
  date: string
  link: string
}

interface ImpactChain {
  news_index: number
  news_snippet: string
  impact_chain: string
  affected_metric: string
  direction: string
  sentiment: string
  confidence: number
  expectation_reasoning: string
  think_count: number
}

interface TreemapData {
  factor: string
  impact: number
  abs_impact: number
}

interface NewsAnalyzerProps {
  ticker: string
}

export default function NewsAnalyzer({ ticker }: NewsAnalyzerProps) {
  const [news, setNews] = useState<NewsItem[]>([])
  const [impactChains, setImpactChains] = useState<ImpactChain[]>([])
  const [macroData, setMacroData] = useState<TreemapData[]>([])
  const [microData, setMicroData] = useState<TreemapData[]>([])
  const [loading, setLoading] = useState(false)
  const [progressCurrent, setProgressCurrent] = useState(0)
  const [progressTotal, setProgressTotal] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [customNews, setCustomNews] = useState('')
  const [showCustomInput, setShowCustomInput] = useState(false)
  const [currentTab, setCurrentTab] = useState<'news' | 'treemap'>('news')
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  const fetchNews = async () => {
    setLoading(true)
    setProgressCurrent(0)
    setProgressTotal(0)
    setProgressMessage('Fetching news...')
    
    try {
      const response = await axios.post('http://localhost:8000/api/news', {
        ticker,
        days: 30,
      })
      
      const newsData = response.data.news.slice(0, 10) // Limit to 10 news
      setNews(newsData)
      setProgressTotal(newsData.length)
      
      // Analyze impact
      await analyzeImpact(newsData, response.data.dates, response.data.links)
    } catch (error) {
      console.error('Error fetching news:', error)
      alert('Failed to fetch news. Please ensure the API server is running.')
    } finally {
      setLoading(false)
      setTimeout(() => {
        setProgressCurrent(0)
        setProgressTotal(0)
        setProgressMessage('')
      }, 1000)
    }
  }

  const analyzeImpact = async (newsItems: NewsItem[], dates: string[], links: string[]) => {
    try {
      const newsTexts = newsItems.map(n => n.news)
      
      // Track progress: analyzing news
      setProgressMessage('Analyzing news impact...')
      setProgressCurrent(0)
      
      const response = await axios.post('http://localhost:8000/api/analyze-impact', {
        ticker,
        news_list: newsTexts,
        dates,
        links,
      })
      
      // Progress: process results
      setProgressMessage('Processing results...')
      
      // Show progress as results are processed
      const impactChains = response.data.impact_chains
      for (let i = 0; i < impactChains.length; i++) {
        setProgressCurrent(i + 1)
        setProgressMessage(`Analyzing news ${i + 1}/${impactChains.length}...`)
        await new Promise(resolve => setTimeout(resolve, 200))
      }
      
      setImpactChains(impactChains)
      setMacroData(response.data.macro_data)
      setMicroData(response.data.micro_data)
      
      setProgressMessage('Complete!')
    } catch (error) {
      console.error('Error analyzing impact:', error)
    }
  }
  
  const toggleRowExpansion = (index: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedRows(newExpanded)
  }

  const handleCustomNews = async () => {
    if (!customNews.trim()) return
    
    setLoading(true)
    try {
      const response = await axios.post('http://localhost:8000/api/custom-news-impact', {
        news_text: customNews,
        ticker,
      })
      
      setImpactChains(response.data.impact_chains)
      setMacroData(response.data.macro_data)
      setMicroData(response.data.micro_data)
      setCurrentTab('treemap')
      setCustomNews('')
      setShowCustomInput(false)
    } catch (error) {
      console.error('Error analyzing custom news:', error)
    } finally {
      setLoading(false)
    }
  }

  const showNewsModal = (index: number) => {
    const chain = impactChains.find(c => c.news_index === index)
    if (chain) {
      const modalBody = document.getElementById('newsModalBody')
      if (modalBody) {
        const newsItem = news[index - 1]
        modalBody.innerHTML = `
          <div style="margin-bottom: 15px;">
            <strong style="color: #808080;">📅 Date:</strong> ${newsItem?.date || 'N/A'}
          </div>
          <div style="margin-bottom: 15px; line-height: 1.6;">
            ${chain.news_snippet}
          </div>
          <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
            ${newsItem?.link ? `<a href="${newsItem.link}" target="_blank" rel="noopener noreferrer" style="color: #808080; text-decoration: none; font-weight: 500;">🔗 Read Full Article →</a>` : ''}
          </div>
        `
        const modal = document.getElementById('newsModal')
        if (modal) modal.classList.add('active')
      }
    }
  }

  const closeNewsModal = () => {
    const modal = document.getElementById('newsModal')
    if (modal) modal.classList.remove('active')
  }

  const downloadCSV = () => {
    const headers = ['date', 'news', 'financial_impact', 'reasoning', 'sentiment', 'confidence']
    const csvContent = [
      headers.join(','),
      ...impactChains.map((chain, idx) => {
        const direction = chain.direction === 'Increase' ? '↑' : chain.direction === 'Decrease' ? '↓' : '→'
        return [
          `"${news[idx]?.date || ''}"`,
          `"${chain.news_snippet.replace(/"/g, '""')}"`,
          `"${chain.affected_metric} ${direction}"`,
          `"${chain.expectation_reasoning.replace(/"/g, '""')}"`,
          `"${chain.sentiment || ''}"`,
          chain.confidence || 0
        ].join(',')
      })
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `${ticker}_news_impact_analysis.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  useEffect(() => {
    if (ticker) {
      fetchNews()
    }
  }, [ticker])

  return (
    <div className={styles.container}>
      {progressTotal > 0 && (
        <RealProgressBar 
          current={progressCurrent}
          total={progressTotal}
          message={progressMessage}
        />
      )}
      <div className={styles.header}>
        <h2 className={styles.title}>{ticker} Analysis</h2>
        <div className={styles.actions}>
          <button
            onClick={() => setShowCustomInput(!showCustomInput)}
            className={styles.button}
          >
            {showCustomInput ? 'Cancel' : '+ Custom News'}
          </button>
          <button onClick={fetchNews} className={styles.button}>
            Refresh
          </button>
        </div>
      </div>

      {/* Custom News Input */}
      {showCustomInput && (
        <div className={styles.customInput}>
          <textarea
            value={customNews}
            onChange={(e) => setCustomNews(e.target.value)}
            placeholder="Enter market news to analyze impact..."
            className={styles.textarea}
            rows={3}
          />
          <button onClick={handleCustomNews} className={styles.submitButton}>
            Analyze Impact
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>Loading...</p>
        </div>
      )}

      {/* Tabs */}
      {!loading && (news.length > 0 || impactChains.length > 0) && (
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${currentTab === 'news' ? styles.active : ''}`}
            onClick={() => setCurrentTab('news')}
          >
            News Impact ({news.length})
          </button>
          <button
            className={`${styles.tab} ${currentTab === 'treemap' ? styles.active : ''}`}
            onClick={() => setCurrentTab('treemap')}
          >
            Treemap Analysis
          </button>
        </div>
      )}

      {/* CSV Download Button */}
      {!loading && currentTab === 'news' && impactChains.length > 0 && (
        <div style={{ marginBottom: '20px', textAlign: 'right' }}>
          <button onClick={downloadCSV} className={styles.downloadBtn}>
            📥 Download CSV
          </button>
        </div>
      )}

      {/* Excel-style Table */}
      {!loading && currentTab === 'news' && (
        <div className={styles.excelTableContainer}>
          <table className={styles.excelTable}>
            <thead>
              <tr className={styles.tableHeader}>
                <th className={styles.headerCell}>News</th>
                <th className={styles.headerCell}>Financial Impact</th>
                <th className={styles.headerCell}>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {impactChains.map((chain, idx) => {
                const direction = chain.direction === 'Increase' ? '↑' : chain.direction === 'Decrease' ? '↓' : '→';
                const isExpanded = expandedRows.has(idx)
                const newsItem = news[idx]
                
                return (
                  <React.Fragment key={chain.news_index}>
                    <tr 
                      className={styles.tableRow} 
                      onClick={() => showNewsModal(chain.news_index)}
                    >
                      <td className={`${styles.tableCell} ${styles.newsCell}`}>
                        <div style={{ fontSize: '0.75em', color: '#808080', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {newsItem?.date && <span>📅 {newsItem.date}</span>}
                          {newsItem?.link && (
                            <a 
                              href={newsItem.link} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className={styles.externalLink}
                            >
                              🔗 External Link
                            </a>
                          )}
                        </div>
                        <div>{chain.news_snippet}</div>
                      </td>
                      <td className={`${styles.tableCell} ${styles.impactCell} ${styles[chain.sentiment.toLowerCase()]}`}>
                        <span>{chain.affected_metric} {direction}</span>
                      </td>
                      <td className={`${styles.tableCell} ${styles.reasoningCell}`}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{chain.expectation_reasoning.slice(0, 100)}{chain.expectation_reasoning.length > 100 ? '...' : ''}</span>
                          {chain.expectation_reasoning.length > 100 && (
                            <button 
                              onClick={(e) => {
                                e.stopPropagation()
                                toggleRowExpansion(idx)
                              }}
                              className={styles.expandButton}
                            >
                              {isExpanded ? '↓ Less' : '↑ More'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className={styles.expandedRow}>
                        <td colSpan={3} className={styles.expandedCell}>
                          <strong>Full Reasoning:</strong><br/>
                          {chain.expectation_reasoning}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && currentTab === 'treemap' && (macroData.length > 0 || microData.length > 0) && (
        <Treemap macroData={macroData} microData={microData} />
      )}

        {/* Empty State */}
        {!loading && news.length === 0 && impactChains.length === 0 && (
          <div className={styles.emptyState}>
            <p>No news data available. Click "Refresh" to fetch news.</p>
          </div>
        )}

        {/* News Modal */}
        <div id="newsModal" className={styles.newsModal}>
          <div className={styles.newsModalContent}>
            <div className={styles.newsModalHeader}>
              <h3 className={styles.newsModalTitle}>Full News</h3>
              <button className={styles.newsModalClose} onClick={closeNewsModal}>×</button>
            </div>
            <div id="newsModalBody" className={styles.newsModalBody}></div>
          </div>
        </div>
      </div>
    )
}
