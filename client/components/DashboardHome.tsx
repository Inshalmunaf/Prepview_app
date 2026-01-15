'use client'

import { useEffect, useState } from 'react'

export default function DashboardHome() {
  const [user, setUser] = useState<any>(null)
  const [interviewCount, setInterviewCount] = useState(0)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    }
    fetchInterviewCount()

    // Listen for refresh events
    const handleRefresh = () => {
      fetchInterviewCount()
    }
    window.addEventListener('dashboard-refresh', handleRefresh)
    return () => window.removeEventListener('dashboard-refresh', handleRefresh)
  }, [])

  const fetchInterviewCount = async () => {
    const token = localStorage.getItem('token')
    if (!token) return

    try {
      const response = await fetch('http://localhost:5000/api/interview/count', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setInterviewCount(data.count)
      }
    } catch (error) {
      console.error('Error fetching interview count:', error)
    }
  }

  const stats = [
    { label: 'Interviews Completed', value: interviewCount.toString(), icon: '📊' },
    { label: 'Average Score', value: 'N/A', icon: '⭐' },
    { label: 'Total Practice Time', value: '0h', icon: '⏱️' },
    { label: 'Skills Improved', value: '0', icon: '🚀' },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-text-primary mb-2">
          Welcome back{user?.name ? `, ${user.name}` : ''}!
        </h1>
        <p className="text-gray-600">Ready to ace your next interview? Let's get started.</p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat, index) => (
          <div
            key={index}
            className="bg-white rounded-xl shadow-md p-6 border border-border hover:shadow-lg transition-shadow"
          >
            <div className="text-3xl mb-2">{stat.icon}</div>
            <div className="text-3xl font-bold text-text-primary mb-1">{stat.value}</div>
            <div className="text-sm text-gray-600">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl shadow-md p-6 border border-border">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <button className="w-full text-left px-4 py-3 bg-primary bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-colors border border-primary border-opacity-20">
              <div className="font-semibold text-text-primary">Start New Interview</div>
              <div className="text-sm text-gray-600">Practice with AI-powered interviews</div>
            </button>
            <button className="w-full text-left px-4 py-3 bg-accent bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-colors border border-accent border-opacity-20">
              <div className="font-semibold text-text-primary">Update Resume</div>
              <div className="text-sm text-gray-600">Edit your CV information</div>
            </button>
            <button className="w-full text-left px-4 py-3 bg-primary bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-colors border border-primary border-opacity-20">
              <div className="font-semibold text-text-primary">View Performance</div>
              <div className="text-sm text-gray-600">Check your progress and analytics</div>
            </button>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-md p-6 border border-border">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Recent Activity</h2>
          <div className="text-center py-8 text-gray-500">
            <p>No recent activity</p>
            <p className="text-sm mt-2">Start practicing to see your activity here</p>
          </div>
        </div>
      </div>
    </div>
  )
}

