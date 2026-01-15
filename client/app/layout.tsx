import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PrepView - AI Interview Simulator',
  description: 'Master your interview skills with AI-powered practice sessions',
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

