'use client'

import { useState, useEffect } from 'react'

interface CVData {
  personalInfo: {
    fullName: string
    email: string
    phone: string
    linkedin: string
    github: string
  }
  summary: string
  skills: string[]
  projects: Array<{
    title: string
    role: string
    techStack: string
    description: string
  }>
  education: Array<{
    degree: string
    institution: string
    graduationYear: string
    fyp?: string
  }>
  experience?: Array<{
    jobTitle: string
    company: string
    startDate: string
    endDate: string
    responsibilities: string
  }>
}

export default function DashboardResume() {
  const [cvData, setCvData] = useState<CVData | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    fetchResume()
  }, [])

  const fetchResume = async () => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch('http://localhost:5000/api/cv', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        // Extract CV fields (Prisma returns JSON fields as objects)
        setCvData({
          personalInfo: data.personalInfo || {},
          summary: data.summary || '',
          skills: data.skills || [],
          projects: data.projects || [],
          education: data.education || [],
          experience: data.experience || [],
        })
      }
    } catch (error) {
      console.error('Error fetching resume:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async () => {
    if (!cvData) return
    const token = localStorage.getItem('token')
    try {
      const response = await fetch('http://localhost:5000/api/cv', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(cvData),
      })
      if (response.ok) {
        setEditing(false)
        alert('Resume updated successfully!')
      }
    } catch (error) {
      console.error('Error updating resume:', error)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (!cvData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-xl shadow-md p-8 text-center">
          <p className="text-gray-600 mb-4">No resume found. Please create one first.</p>
          <a
            href="/cv-creation"
            className="inline-block bg-button-primary text-white px-6 py-2 rounded-lg hover:opacity-90 transition-colors"
          >
            Create Resume
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-4xl font-bold text-text-primary">My Resume</h1>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="bg-button-primary text-white px-6 py-2 rounded-lg hover:opacity-90 transition-colors"
          >
            Edit Resume
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-md p-8 border border-border">
        {editing ? (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
              <input
                type="text"
                value={cvData.personalInfo.fullName}
                onChange={(e) =>
                  setCvData({
                    ...cvData,
                    personalInfo: { ...cvData.personalInfo, fullName: e.target.value },
                  })
                }
                className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                type="email"
                value={cvData.personalInfo.email}
                onChange={(e) =>
                  setCvData({
                    ...cvData,
                    personalInfo: { ...cvData.personalInfo, email: e.target.value },
                  })
                }
                className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Summary</label>
              <textarea
                value={cvData.summary}
                onChange={(e) => setCvData({ ...cvData, summary: e.target.value })}
                rows={4}
                className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-accent"
              />
            </div>
            <div className="flex gap-4">
              <button
                onClick={handleUpdate}
                className="bg-button-primary text-white px-6 py-2 rounded-lg hover:opacity-90 transition-colors"
              >
                Save Changes
              </button>
              <button
                onClick={() => setEditing(false)}
                className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="border-b-2 border-primary pb-4">
              <h2 className="text-3xl font-bold text-text-primary">{cvData.personalInfo.fullName}</h2>
              <div className="text-gray-600 mt-2">
                {cvData.personalInfo.email} • {cvData.personalInfo.phone}
              </div>
            </div>
            {cvData.summary && (
              <div>
                <h3 className="text-xl font-bold text-text-primary mb-2">Professional Summary</h3>
                <p className="text-gray-700">{cvData.summary}</p>
              </div>
            )}
            {cvData.skills && cvData.skills.length > 0 && (
              <div>
                <h3 className="text-xl font-bold text-text-primary mb-2">Technical Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {cvData.skills.filter((s) => s.trim()).map((skill, index) => (
                    <span
                      key={index}
                      className="bg-primary bg-opacity-20 text-primary px-3 py-1 rounded-full text-sm font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {cvData.projects && cvData.projects.length > 0 && (
              <div>
                <h3 className="text-xl font-bold text-text-primary mb-2">Projects</h3>
                {cvData.projects.map((project, index) => (
                  <div key={index} className="mb-4">
                    <h4 className="font-bold text-text-primary">{project.title}</h4>
                    <p className="text-accent text-sm">{project.role}</p>
                    {project.techStack && (
                      <p className="text-accent text-sm mt-1">
                        <span className="font-semibold">Tech Stack:</span> {project.techStack}
                      </p>
                    )}
                    <p className="text-gray-700 mt-2">{project.description}</p>
                  </div>
                ))}
              </div>
            )}
            {cvData.education && cvData.education.length > 0 && (
              <div>
                <h3 className="text-xl font-bold text-text-primary mb-2">Education</h3>
                {cvData.education.map((edu, index) => (
                  <div key={index} className="mb-3">
                    <h4 className="font-bold text-text-primary">{edu.degree}</h4>
                    <p className="text-accent">{edu.institution} • {edu.graduationYear}</p>
                    {edu.fyp && (
                      <p className="text-gray-600 text-sm mt-1">
                        <span className="font-semibold">FYP:</span> {edu.fyp}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
            {cvData.experience && cvData.experience.length > 0 && (
              <div>
                <h3 className="text-xl font-bold text-text-primary mb-2">Work Experience</h3>
                {cvData.experience.map((exp, index) => (
                  <div key={index} className="mb-4">
                    <h4 className="font-bold text-text-primary">{exp.jobTitle}</h4>
                    <p className="text-accent">{exp.company} • {exp.startDate} - {exp.endDate}</p>
                    <p className="text-gray-700 mt-1">{exp.responsibilities}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

