'use client'

export default function Reviews() {
  const reviews = [
    {
      name: 'Sarah Chen',
      role: 'Software Engineer',
      company: 'Tech Corp',
      content: 'PrepView helped me land my dream job at a FAANG company. The AI interviews were incredibly realistic and the feedback was spot-on.',
      rating: 5,
      avatar: '👩‍💻',
    },
    {
      name: 'Michael Rodriguez',
      role: 'Data Scientist',
      company: 'Data Insights',
      content: 'The coding challenges and real-time feedback improved my problem-solving skills significantly. Highly recommend!',
      rating: 5,
      avatar: '👨‍🔬',
    },
    {
      name: 'Emily Johnson',
      role: 'Full Stack Developer',
      company: 'StartupXYZ',
      content: 'Best investment I made in my career. The performance analytics helped me identify and fix my weak areas.',
      rating: 5,
      avatar: '👩‍💼',
    },
  ]

  return (
    <section id="reviews" className="py-20 px-4 sm:px-6 lg:px-8 bg-background">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">
            What Our Users Say
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Join thousands of professionals who have improved their interview skills
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {reviews.map((review, index) => (
            <div
              key={index}
              className="bg-white rounded-xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 border border-border"
            >
              <div className="flex items-center mb-4">
                <div className="text-4xl mr-4">{review.avatar}</div>
                <div>
                  <h4 className="font-bold text-text-primary">{review.name}</h4>
                  <p className="text-sm text-gray-600">
                    {review.role} at {review.company}
                  </p>
                </div>
              </div>
              <div className="flex mb-4">
                {[...Array(review.rating)].map((_, i) => (
                  <span key={i} className="text-warning text-xl">★</span>
                ))}
              </div>
              <p className="text-gray-700 leading-relaxed italic">
                "{review.content}"
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

