'use client'

import styles from './RealProgressBar.module.css'

interface RealProgressBarProps {
  current: number  // Current news item being analyzed
  total: number    // Total news items
  message: string  // Current status message
}

export default function RealProgressBar({ current, total, message }: RealProgressBarProps) {
  const progress = total > 0 ? Math.round((current / total) * 100) : 0

  return (
    <div className={styles.container}>
      <div className={styles.progressWrapper}>
        <div className={styles.progressBar}>
          <div 
            className={styles.progressFill} 
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className={styles.info}>
          <div className={styles.message}>{message}</div>
          <div className={styles.count}>
            {current} / {total} news items analyzed
          </div>
        </div>
      </div>
    </div>
  )
}

