'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

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

export default function CVCreationPage() {
  const router = useRouter()
  const [cvData, setCvData] = useState<CVData>({
    personalInfo: {
      fullName: '',
      email: '',
      phone: '',
      linkedin: '',
      github: '',
    },
    summary: '',
    skills: [''],
    projects: [{ title: '', role: '', techStack: '', description: '' }],
    education: [{ degree: '', institution: '', graduationYear: '', fyp: '' }],
    experience: [],
  })

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
    }
  }, [router])

  const handlePersonalInfoChange = (field: string, value: string) => {
    setCvData({
      ...cvData,
      personalInfo: {
        ...cvData.personalInfo,
        [field]: value,
      },
    })
  }

  const handleProjectChange = (index: number, field: string, value: string) => {
    const newProjects = [...cvData.projects]
    newProjects[index] = { ...newProjects[index], [field]: value }
    setCvData({ ...cvData, projects: newProjects })
  }

  const addProject = () => {
    setCvData({
      ...cvData,
      projects: [...cvData.projects, { title: '', role: '', techStack: '', description: '' }],
    })
  }

  const removeProject = (index: number) => {
    const newProjects = cvData.projects.filter((_, i) => i !== index)
    setCvData({ ...cvData, projects: newProjects })
  }

  const handleEducationChange = (index: number, field: string, value: string) => {
    const newEducation = [...cvData.education]
    newEducation[index] = { ...newEducation[index], [field]: value }
    setCvData({ ...cvData, education: newEducation })
  }

  const addEducation = () => {
    setCvData({
      ...cvData,
      education: [...cvData.education, { degree: '', institution: '', graduationYear: '', fyp: '' }],
    })
  }

  const handleExperienceChange = (index: number, field: string, value: string) => {
    const newExperience = [...(cvData.experience || [])]
    newExperience[index] = { ...newExperience[index], [field]: value }
    setCvData({ ...cvData, experience: newExperience })
  }

  const addExperience = () => {
    setCvData({
      ...cvData,
      experience: [...(cvData.experience || []), { jobTitle: '', company: '', startDate: '', endDate: '', responsibilities: '' }],
    })
  }

  const removeExperience = (index: number) => {
    const newExperience = (cvData.experience || []).filter((_, i) => i !== index)
    setCvData({ ...cvData, experience: newExperience })
  }

  const handleSkillChange = (index: number, value: string) => {
    const newSkills = [...cvData.skills]
    newSkills[index] = value
    setCvData({ ...cvData, skills: newSkills })
  }

  const addSkill = () => {
    setCvData({
      ...cvData,
      skills: [...cvData.skills, ''],
    })
  }

  const handleSave = async () => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch('http://localhost:5000/api/cv', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(cvData),
      })

      if (response.ok) {
        router.push('/dashboard')
      }
    } catch (error) {
      console.error('Error saving CV:', error)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">P</span>
            </div>
            <span className="text-2xl font-bold text-primary">
              PrepView
            </span>
          </Link>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Create Your Resume</h1>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Side - Input Fields */}
          <div className="space-y-6">
            {/* Personal Information */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Personal Information</h2>
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Full Name"
                  value={cvData.personalInfo.fullName}
                  onChange={(e) => handlePersonalInfoChange('fullName', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={cvData.personalInfo.email}
                  onChange={(e) => handlePersonalInfoChange('email', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <input
                  type="tel"
                  placeholder="Phone"
                  value={cvData.personalInfo.phone}
                  onChange={(e) => handlePersonalInfoChange('phone', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <input
                  type="text"
                  placeholder="LinkedIn URL"
                  value={cvData.personalInfo.linkedin}
                  onChange={(e) => handlePersonalInfoChange('linkedin', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <input
                  type="text"
                  placeholder="GitHub URL"
                  value={cvData.personalInfo.github}
                  onChange={(e) => handlePersonalInfoChange('github', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Professional Summary */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Professional Summary</h2>
              <p className="text-sm text-gray-600 mb-2">Write your career goal (3-4 lines max)</p>
              <textarea
                placeholder="Write a brief summary about yourself and your career goals..."
                value={cvData.summary}
                onChange={(e) => setCvData({ ...cvData, summary: e.target.value })}
                rows={4}
                maxLength={500}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            {/* Technical Skills - High Priority */}
            <div className="bg-white rounded-lg shadow-md p-6 border-2 border-primary-500">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Technical Skills</h2>
                  <p className="text-sm text-gray-600">Add skills as tags (e.g., Python, React, SQL)</p>
                </div>
                <button
                  onClick={addSkill}
                  className="text-primary-600 hover:text-primary-700 font-semibold"
                >
                  + Add
                </button>
              </div>
              <div className="space-y-2">
                {cvData.skills.map((skill, index) => (
                  <input
                    key={index}
                    type="text"
                    placeholder="Skill (e.g., Python, React, Node.js)"
                    value={skill}
                    onChange={(e) => handleSkillChange(index, e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                ))}
              </div>
            </div>

            {/* Projects - High Priority */}
            <div className="bg-white rounded-lg shadow-md p-6 border-2 border-primary-500">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Projects</h2>
                  <p className="text-sm text-gray-600">Showcase your projects (Most important for AI)</p>
                </div>
                <button
                  onClick={addProject}
                  className="text-primary-600 hover:text-primary-700 font-semibold"
                >
                  + Add
                </button>
              </div>
              {cvData.projects.map((project, index) => (
                <div key={index} className="mb-4 space-y-2 border-b pb-4 last:border-0">
                  <input
                    type="text"
                    placeholder="Project Title (e.g., Chat Application)"
                    value={project.title}
                    onChange={(e) => handleProjectChange(index, 'title', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <input
                    type="text"
                    placeholder="Role (e.g., Backend Developer)"
                    value={project.role}
                    onChange={(e) => handleProjectChange(index, 'role', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <input
                    type="text"
                    placeholder="Tech Stack (e.g., Node.js, Socket.io, MongoDB)"
                    value={project.techStack}
                    onChange={(e) => handleProjectChange(index, 'techStack', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <textarea
                    placeholder="Description / Impact (e.g., Reduced latency by 20%...)"
                    value={project.description}
                    onChange={(e) => handleProjectChange(index, 'description', e.target.value)}
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  {cvData.projects.length > 1 && (
                    <button
                      onClick={() => removeProject(index)}
                      className="text-red-600 hover:text-red-700 text-sm"
                    >
                      Remove Project
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Education */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">Education</h2>
                <button
                  onClick={addEducation}
                  className="text-primary-600 hover:text-primary-700 font-semibold"
                >
                  + Add
                </button>
              </div>
              {cvData.education.map((edu, index) => (
                <div key={index} className="mb-4 space-y-2 border-b pb-4 last:border-0">
                  <input
                    type="text"
                    placeholder="Degree Name (e.g., BSc Computer Science)"
                    value={edu.degree}
                    onChange={(e) => handleEducationChange(index, 'degree', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <input
                    type="text"
                    placeholder="Institute"
                    value={edu.institution}
                    onChange={(e) => handleEducationChange(index, 'institution', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <input
                    type="text"
                    placeholder="Graduation Year"
                    value={edu.graduationYear}
                    onChange={(e) => handleEducationChange(index, 'graduationYear', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <input
                    type="text"
                    placeholder="Final Year Project (FYP) - Optional"
                    value={edu.fyp || ''}
                    onChange={(e) => handleEducationChange(index, 'fyp', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              ))}
            </div>

            {/* Work Experience - Optional/Low Priority */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Work Experience (Optional)</h2>
                  <p className="text-sm text-gray-600">For fresh graduates, this section is optional</p>
                </div>
                <button
                  onClick={addExperience}
                  className="text-primary-600 hover:text-primary-700 font-semibold"
                >
                  + Add
                </button>
              </div>
              {cvData.experience && cvData.experience.length > 0 ? (
                cvData.experience.map((exp, index) => (
                  <div key={index} className="mb-4 space-y-2 border-b pb-4 last:border-0">
                    <input
                      type="text"
                      placeholder="Job Title"
                      value={exp.jobTitle}
                      onChange={(e) => handleExperienceChange(index, 'jobTitle', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <input
                      type="text"
                      placeholder="Company"
                      value={exp.company}
                      onChange={(e) => handleExperienceChange(index, 'company', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="Start Date (e.g., Jan 2020)"
                        value={exp.startDate}
                        onChange={(e) => handleExperienceChange(index, 'startDate', e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                      <input
                        type="text"
                        placeholder="End Date (e.g., Present)"
                        value={exp.endDate}
                        onChange={(e) => handleExperienceChange(index, 'endDate', e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                    </div>
                    <textarea
                      placeholder="Responsibilities"
                      value={exp.responsibilities}
                      onChange={(e) => handleExperienceChange(index, 'responsibilities', e.target.value)}
                      rows={2}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <button
                      onClick={() => removeExperience(index)}
                      className="text-red-600 hover:text-red-700 text-sm"
                    >
                      Remove Experience
                    </button>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm italic">No work experience added. Click "+ Add" to add experience.</p>
              )}
            </div>

            <button
              onClick={handleSave}
              className="w-full bg-button-primary text-white py-3 rounded-lg font-semibold hover:opacity-90 transition-all shadow-lg hover:shadow-xl"
            >
              Save & Continue to Dashboard
            </button>
          </div>

          {/* Right Side - CV Preview */}
          <div className="lg:sticky lg:top-8 h-fit">
            <div className="bg-white rounded-lg shadow-xl p-8 border-2 border-border">
              <div className="space-y-6">
                {/* Header */}
                <div className="border-b-2 border-primary-600 pb-4">
                  <h1 className="text-3xl font-bold text-gray-900">
                    {cvData.personalInfo.fullName || 'Your Name'}
                  </h1>
                  <div className="flex flex-wrap gap-2 text-sm text-gray-600 mt-2">
                    {cvData.personalInfo.email && <span>{cvData.personalInfo.email}</span>}
                    {cvData.personalInfo.phone && <span>• {cvData.personalInfo.phone}</span>}
                  </div>
                  <div className="flex gap-4 text-sm text-primary-600 mt-2">
                    {cvData.personalInfo.linkedin && (
                      <a href={cvData.personalInfo.linkedin} target="_blank" rel="noopener noreferrer">
                        LinkedIn
                      </a>
                    )}
                    {cvData.personalInfo.github && (
                      <a href={cvData.personalInfo.github} target="_blank" rel="noopener noreferrer">
                        GitHub
                      </a>
                    )}
                  </div>
                </div>

                {/* Professional Summary */}
                {cvData.summary && (
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2 border-b border-gray-300 pb-1">
                      Professional Summary
                    </h2>
                    <p className="text-gray-700">{cvData.summary}</p>
                  </div>
                )}

                {/* Technical Skills - High Priority */}
                {cvData.skills.some((skill) => skill.trim()) && (
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2 border-b border-gray-300 pb-1">
                      Technical Skills
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {cvData.skills.filter((skill) => skill.trim()).map((skill, index) => (
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

                {/* Projects - High Priority */}
                {cvData.projects.some((proj) => proj.title) && (
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2 border-b border-gray-300 pb-1">
                      Projects
                    </h2>
                    {cvData.projects.map((project, index) => (
                      project.title && (
                        <div key={index} className="mb-4">
                          <h3 className="font-bold text-gray-900">{project.title}</h3>
                          <p className="text-primary-600 text-sm">{project.role}</p>
                          {project.techStack && (
                            <p className="text-accent text-sm mt-1">
                              <span className="font-semibold">Tech Stack:</span> {project.techStack}
                            </p>
                          )}
                          <p className="text-gray-700 mt-2">{project.description}</p>
                        </div>
                      )
                    ))}
                  </div>
                )}

                {/* Education */}
                {cvData.education.some((edu) => edu.institution) && (
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2 border-b border-gray-300 pb-1">
                      Education
                    </h2>
                    {cvData.education.map((edu, index) => (
                      edu.institution && (
                        <div key={index} className="mb-3">
                          <h3 className="font-bold text-gray-900">{edu.degree}</h3>
                          <p className="text-primary-600">{edu.institution} • {edu.graduationYear}</p>
                          {edu.fyp && (
                            <p className="text-gray-600 text-sm mt-1">
                              <span className="font-semibold">FYP:</span> {edu.fyp}
                            </p>
                          )}
                        </div>
                      )
                    ))}
                  </div>
                )}

                {/* Work Experience - Optional/Low Priority */}
                {cvData.experience && cvData.experience.some((exp) => exp.company) && (
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2 border-b border-gray-300 pb-1">
                      Work Experience
                    </h2>
                    {cvData.experience.map((exp, index) => (
                      exp.company && (
                        <div key={index} className="mb-4">
                          <h3 className="font-bold text-gray-900">{exp.jobTitle}</h3>
                          <p className="text-primary-600">{exp.company} • {exp.startDate} - {exp.endDate}</p>
                          <p className="text-gray-700 mt-1">{exp.responsibilities}</p>
                        </div>
                      )
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

