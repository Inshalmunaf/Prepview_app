'use client'

export default function DashboardPerformance() {
  const performanceData = [
    { category: 'Problem Solving', score: 0, maxScore: 100 },
    { category: 'Code Quality', score: 0, maxScore: 100 },
    { category: 'Communication', score: 0, maxScore: 100 },
    { category: 'Time Management', score: 0, maxScore: 100 },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-text-primary mb-2">Performance Analytics</h1>
        <p className="text-gray-600">Track your progress and identify areas for improvement</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl shadow-md p-6 border border-border">
          <h2 className="text-2xl font-bold text-text-primary mb-6">Overall Performance</h2>
          <div className="space-y-6">
            {performanceData.map((item, index) => (
              <div key={index}>
                <div className="flex justify-between mb-2">
                  <span className="font-medium text-text-primary">{item.category}</span>
                  <span className="text-gray-600">{item.score}/{item.maxScore}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-accent h-3 rounded-full transition-all"
                    style={{ width: `${(item.score / item.maxScore) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-md p-6 border border-border">
          <h2 className="text-2xl font-bold text-text-primary mb-6">Interview History</h2>
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg mb-2">No interviews completed yet</p>
            <p className="text-sm">Start practicing to see your performance data here</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-md p-6 border border-border lg:col-span-2">
          <h2 className="text-2xl font-bold text-text-primary mb-6">Improvement Suggestions</h2>
          <div className="bg-primary bg-opacity-10 border border-primary border-opacity-20 rounded-lg p-4">
            <p className="text-gray-700">
              Complete your first interview to receive personalized improvement suggestions based on your performance.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

