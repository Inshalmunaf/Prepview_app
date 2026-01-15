'use client'

export default function Hero() {
  return (
    <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-background">
      <div className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <div className="text-center lg:text-left">
            <h1 className="text-5xl md:text-6xl font-bold text-text-primary mb-6 leading-tight">
              Master Your Interview Skills with
              <span className="text-accent">
                {' '}AI-Powered Practice
              </span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Prepare for technical interviews with real-time coding challenges,
              AI feedback, and personalized performance insights. Get interview-ready
              in weeks, not months.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <a
                href="/signup"
                className="bg-button-primary text-white px-8 py-4 rounded-lg font-semibold text-lg hover:opacity-90 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-1"
              >
                Get Started Free
              </a>
              <a
                href="#how-it-works"
                className="border-2 border-primary text-primary px-8 py-4 rounded-lg font-semibold text-lg hover:bg-primary hover:text-white transition-all"
              >
                Learn More
              </a>
            </div>
          </div>

          {/* Right Image/Illustration */}
          <div className="relative">
            <div className="relative z-10">
              <div className="bg-gradient-to-br from-primary-100 to-secondary-100 rounded-2xl p-8 shadow-2xl">
                <div className="bg-white rounded-xl p-6 shadow-lg">
                  <div className="space-y-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                    <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-green-400">
                      <div>$ npm install prepview</div>
                      <div className="mt-2 text-gray-400">Preparing your interview...</div>
                      <div className="mt-2 text-green-400">✓ Ready to ace your interview!</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-6 -right-6 w-64 h-64 bg-primary-200 rounded-full blur-3xl opacity-50"></div>
            <div className="absolute -top-6 -left-6 w-64 h-64 bg-secondary-200 rounded-full blur-3xl opacity-50"></div>
          </div>
        </div>
      </div>
    </section>
  )
}

