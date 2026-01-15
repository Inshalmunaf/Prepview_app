'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import DashboardNavbar from '@/components/DashboardNavbar'
import DashboardHome from '@/components/DashboardHome'
import DashboardResume from '@/components/DashboardResume'
import DashboardInterview from '@/components/DashboardInterview'
import DashboardPerformance from '@/components/DashboardPerformance'

export default function DashboardPage() {
  const [activeSection, setActiveSection] = useState('dashboard')
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
    }
  }, [router])

  // Refresh data when component becomes visible (e.g., returning from interview)
  useEffect(() => {
    const handleFocus = () => {
      // Trigger a refresh of dashboard data
      window.dispatchEvent(new Event('dashboard-refresh'))
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [])

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar activeSection={activeSection} setActiveSection={setActiveSection} />
      <div className="pt-16">
        {activeSection === 'dashboard' && <DashboardHome />}
        {activeSection === 'resume' && <DashboardResume />}
        {activeSection === 'interview' && <DashboardInterview />}
        {activeSection === 'performance' && <DashboardPerformance />}
      </div>
    </div>
  )
}

