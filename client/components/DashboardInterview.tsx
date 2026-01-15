'use client'

import { useRouter } from 'next/navigation'

interface InterviewCard {
  id: string
  topic: string
  duration: string
  coverage: string[]
  image: string
}

export default function DashboardInterview() {
  const router = useRouter()

  const interviewFields: InterviewCard[] = [
    {
      id: 'data-science',
      topic: 'Data Science',
      duration: '45 minutes',
      coverage: ['Python', 'Machine Learning', 'Statistics', 'Data Analysis'],
      image: '📊',
    },
    {
      id: 'software-engineering',
      topic: 'Software Engineering',
      duration: '60 minutes',
      coverage: ['Algorithms', 'Data Structures', 'System Design', 'Problem Solving'],
      image: '💻',
    },
    {
      id: 'frontend-development',
      topic: 'Frontend Development',
      duration: '45 minutes',
      coverage: ['React', 'JavaScript', 'CSS', 'Web APIs'],
      image: '🎨',
    },
    {
      id: 'backend-development',
      topic: 'Backend Development',
      duration: '50 minutes',
      coverage: ['Node.js', 'Databases', 'APIs', 'System Architecture'],
      image: '⚙️',
    },
    {
      id: 'devops',
      topic: 'DevOps',
      duration: '40 minutes',
      coverage: ['Docker', 'Kubernetes', 'CI/CD', 'Cloud Services'],
      image: '🚀',
    },
    {
      id: 'full-stack',
      topic: 'Full Stack Development',
      duration: '75 minutes',
      coverage: ['Full Stack', 'MERN Stack', 'Database Design', 'Deployment'],
      image: '🌐',
    },
    {
      id: 'mobile-development',
      topic: 'Mobile Development',
      duration: '45 minutes',
      coverage: ['React Native', 'iOS', 'Android', 'Mobile APIs'],
      image: '📱',
    },
    {
      id: 'cybersecurity',
      topic: 'Cybersecurity',
      duration: '50 minutes',
      coverage: ['Security', 'Network Security', 'Encryption', 'Best Practices'],
      image: '🔒',
    },
  ]

  const handleStartInterview = (fieldId: string) => {
    router.push(`/interview/${fieldId}`)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-text-primary mb-2">Choose Your Interview Field</h1>
        <p className="text-gray-600">Select a domain to start practicing with AI-powered interviews</p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {interviewFields.map((field) => (
          <div
            key={field.id}
            className="bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 border border-border overflow-hidden transform hover:-translate-y-2"
          >
            <div className="bg-primary p-8 text-center">
              <div className="text-6xl mb-4">{field.image}</div>
              <h3 className="text-2xl font-bold text-white mb-2">{field.topic}</h3>
              <p className="text-white opacity-80">Duration: {field.duration}</p>
            </div>
            <div className="p-6">
              <h4 className="font-semibold text-text-primary mb-3">What it covers:</h4>
              <ul className="space-y-2 mb-6">
                {field.coverage.map((item, index) => (
                  <li key={index} className="flex items-center text-gray-600">
                    <span className="text-accent mr-2">✓</span>
                    {item}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleStartInterview(field.id)}
                className="w-full bg-button-primary text-white py-3 rounded-lg font-semibold hover:opacity-90 transition-all shadow-md hover:shadow-lg"
              >
                Start Interview
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

