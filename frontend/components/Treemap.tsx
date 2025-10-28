'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'
import styles from './Treemap.module.css'

interface TreemapData {
  factor: string
  impact: number
  abs_impact: number
}

interface TreemapProps {
  macroData: TreemapData[]
  microData: TreemapData[]
}

export default function Treemap({ macroData, microData }: TreemapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [currentData, setCurrentData] = useState<'macro' | 'micro'>('macro')
  const [isFlipped, setIsFlipped] = useState<{ [key: string]: boolean }>({})

  const renderTreemap = () => {
    if (!containerRef.current) return

    // Clear previous render
    d3.select(containerRef.current).selectAll('*').remove()

    const width = containerRef.current.offsetWidth - 4
    const height = 600

    const data = currentData === 'macro' ? macroData : microData

    if (data.length === 0) {
      containerRef.current.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #a0aec0;">No data available</div>'
      return
    }

    // Create treemap layout
    const treemap = d3.treemap()
      .size([width, height])
      .padding(2)

    const root = d3.hierarchy({ children: data })
      .sum((d: any) => d.abs_impact)
      .sort((a, b) => (b.value || 0) - (a.value || 0))

    treemap(root)

    // Create SVG
    const svg = d3.select(containerRef.current)
      .append('svg')
      .attr('width', width)
      .attr('height', height)

    // Create tooltip
    const tooltip = d3.select('body')
      .append('div')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.9)')
      .style('color', 'white')
      .style('padding', '12px 16px')
      .style('border-radius', '8px')
      .style('font-size', '13px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', '1000')
      .style('max-width', '250px')
      .style('box-shadow', '0 8px 25px rgba(0, 0, 0, 0.3)')
      .style('border', '1px solid rgba(102, 126, 234, 0.3)')

    // Create nodes
    const nodes = svg.selectAll('.node')
      .data(root.leaves())
      .enter().append('g')
      .attr('class', 'node')
      .attr('transform', (d: any) => `translate(${d.x0},${d.y0})`)
      .style('cursor', 'pointer')

    // Add rectangles with flip card functionality
    nodes.each(function(d: any) {
      const node = d3.select(this)
      const rectWidth = d.x1 - d.x0
      const rectHeight = d.y1 - d.y0

      // Container for flip card
      const cardContainer = node.append('g')
        .attr('class', 'card-container')
        .style('transform-style', 'preserve-3d')
        .style('transition', 'transform 0.6s')

      // Front face (Impact value)
      const front = cardContainer.append('rect')
        .attr('width', rectWidth)
        .attr('height', rectHeight)
        .style('fill', d.data.impact >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)')
        .style('stroke', '#fff')
        .style('stroke-width', 2)

      // Add impact percentage
      cardContainer.append('text')
        .attr('x', rectWidth / 2)
        .attr('y', rectHeight / 2)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .style('fill', '#ffffff')
        .style('font-size', `${Math.min(rectWidth / 10, 18)}px`)
        .style('font-weight', '900')
        .style('text-shadow', '3px 3px 6px rgba(0,0,0,0.8)')
        .text(`${d.data.impact >= 0 ? '+' : ''}${(d.data.impact * 100).toFixed(1)}%`)

      // Add factor name if space allows
      if (rectWidth > 80 && rectHeight > 40) {
        cardContainer.append('text')
          .attr('x', 6)
          .attr('y', 14)
          .attr('text-anchor', 'start')
          .style('fill', '#ffffff')
          .style('font-size', `${Math.min(rectWidth / 15, 12)}px`)
          .style('font-weight', '700')
          .style('text-shadow', '2px 2px 4px rgba(0,0,0,0.8)')
          .text(d.data.factor.substring(0, 30))
      }

      // Click to show detailed modal
      node.on('click', function(e) {
        const factorName = d.data.factor
        const impactValue = d.data.impact
        
        // Trigger modal via custom event
        const customEvent = new CustomEvent('showFactorModal', { 
          detail: { factor: factorName, impact: impactValue } 
        })
        document.dispatchEvent(customEvent)
      })

      // Hover effects
      node.on('mouseover', function(event) {
        front
          .transition()
          .duration(200)
          .style('stroke-width', 4)
          .style('stroke', '#667eea')
          .style('filter', 'brightness(1.2)')

        tooltip.transition()
          .duration(200)
          .style('opacity', 0.9)

        tooltip.html(`
          <strong>${d.data.factor}</strong><br/>
          <span style="color: ${d.data.impact >= 0 ? '#10b981' : '#ef4444'};">
            Impact: ${(d.data.impact * 100).toFixed(2)}%
          </span><br/>
          <em>Click to flip card</em>
        `)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 28) + 'px')
      })

      node.on('mouseout', function() {
        front
          .transition()
          .duration(200)
          .style('stroke-width', 2)
          .style('stroke', '#fff')
          .style('filter', 'brightness(1)')

        tooltip.transition()
          .duration(500)
          .style('opacity', 0)
      })
    })
  }

  useEffect(() => {
    renderTreemap()
    
    // Listen for custom event from D3
    const handleModalShow = (e: CustomEvent) => {
      showFactorModal(e.detail.factor, e.detail.impact)
    }
    
    document.addEventListener('showFactorModal', handleModalShow as EventListener)
    
    return () => {
      document.removeEventListener('showFactorModal', handleModalShow as EventListener)
    }
  }, [currentData, macroData, microData])

  const closeFactorModal = () => {
    const modal = document.getElementById('factorDetailModal')
    if (modal) modal.classList.remove('show')
  }

  const showFactorModal = useCallback((factorName: string, impactValue: number) => {
    const modal = document.getElementById('factorDetailModal')
    const content = document.getElementById('factorDetailContent')
    if (modal && content) {
      content.innerHTML = `
        <h3 style="color: #808080; margin-bottom: 20px;">Factor: ${factorName}</h3>
        <div style="text-align: left; color: #e0e0e0;">
          <p><strong>Impact:</strong> ${(impactValue * 100).toFixed(2)}%</p>
          <p style="margin-top: 15px;">Detailed analysis coming soon...</p>
        </div>
      `
      modal.classList.add('show')
    }
  }, [])

  return (
    <div className={styles.container}>
      {/* Tabs */}
      <div className={styles.tabContainer}>
        <button
          className={`${styles.tab} ${currentData === 'macro' ? styles.active : ''}`}
          onClick={() => setCurrentData('macro')}
        >
          Macro Factors
        </button>
        <button
          className={`${styles.tab} ${currentData === 'micro' ? styles.active : ''}`}
          onClick={() => setCurrentData('micro')}
        >
          Micro Factors
        </button>
      </div>

      {/* Treemap Container */}
      <div ref={containerRef} className={styles.treemapContainer}></div>

      {/* Legend */}
      <div className={styles.legend}>
        <div className={styles.legendItem}>
          <div className={`${styles.legendColor} ${styles.positive}`}></div>
          <span>Positive Impact</span>
        </div>
        <div className={styles.legendItem}>
          <div className={`${styles.legendColor} ${styles.negative}`}></div>
          <span>Negative Impact</span>
        </div>
      </div>

      {/* Instructions */}
      <div className={styles.instructions}>
        <p>💡 Click on any rectangle to see detailed impact information</p>
      </div>

      {/* Factor Detail Modal */}
      <div id="factorDetailModal" className={styles.factorDetailModal}>
        <div className={styles.modalContent}>
          <button className={styles.modalClose} onClick={closeFactorModal}>×</button>
          <div id="factorDetailContent"></div>
        </div>
      </div>
    </div>
  )
}
