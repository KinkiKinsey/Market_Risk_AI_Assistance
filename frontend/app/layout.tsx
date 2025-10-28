import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Q&Q.AI - Hedge Fund Intelligence Platform',
  description: 'Quantitative & Qualitative AI Investment Analysis System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
