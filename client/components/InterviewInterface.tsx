'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import axios from 'axios';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

interface InterviewInterfaceProps {
  fieldId: string
}

const languages = [
  { value: 'javascript', label: 'JavaScript' },
  { value: 'python', label: 'Python' },
  { value: 'cpp', label: 'C++' },
  { value: 'java', label: 'Java' },
  
]

export default function InterviewInterface({ fieldId }: InterviewInterfaceProps) {
  const router = useRouter()
  // States
  const [isInterviewStarted, setIsInterviewStarted] = useState(false)
  const [currentQuestion, setCurrentQuestion] = useState(1)
  const [totalQuestions] = useState(5)
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null)
  const [recorder, setRecorder] = useState<MediaRecorder | null>(null)
  const [code, setCode] = useState('// Write your code here\n')
  const [selectedLanguage, setSelectedLanguage] = useState('javascript')
  const [output, setOutput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  
  const [isUploading, setIsUploading] = useState(false)
  
  const videoRef = useRef<HTMLVideoElement>(null)
  const smallVideoRef = useRef<HTMLVideoElement>(null)
  const [isRecording, setIsRecording] = useState(false)
  
  // ⚡ CHANGE 1: State ki jagah Ref use karein (Fast & Synchronous)
  const mediaChunksRef = useRef<Blob[]>([]); 
  
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isStopped, setIsStopped] = useState(false)
  const [questions, setQuestion] = useState<any[]>([]) 

  // 👇👇👇 --- UPDATED AI SPEAKING LOGIC --- 👇👇👇

  const speakQuestion = (text: string, onComplete?: () => void) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel(); 

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 0.9;
      utterance.pitch = 1;

      utterance.onend = () => {
        if (onComplete) onComplete();
      };

      utterance.onerror = () => {
        if (onComplete) onComplete();
      };

      window.speechSynthesis.speak(utterance);
    } else {
        if (onComplete) onComplete();
    }
  };

  useEffect(() => {
    if (isInterviewStarted && questions.length > 0 && mediaStream) {
      
      const currentQ = questions[currentQuestion - 1];
      
      if (currentQ) {
        if (recorder && recorder.state === 'recording') {
            recorder.pause();
        }

        const textToRead = `${currentQ.question}. ${currentQ.description}`;
        
        speakQuestion(textToRead, () => {
             console.log("🤖 AI finished speaking. Starting Recording...");
             startRecordingProcess(mediaStream);
        });
      }
    }

    return () => {
      if (typeof window !== 'undefined') {
        window.speechSynthesis.cancel();
      }
    };
  }, [currentQuestion, isInterviewStarted, questions, mediaStream]);

  // 👆👆👆 --- LOGIC ENDS HERE --- 👆👆👆

  const startInterview = async () => {
    try {
      const token = localStorage.getItem('token')
      const sessionResponse = await fetch('http://localhost:5000/api/interview/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ fieldId }),
      })

      const sessionData = await sessionResponse.json()
      if (!sessionResponse.ok) {
        throw new Error(sessionData.message || 'Failed to create session')
      }

      setSessionId(sessionData.sessionId)
      setQuestion(sessionData.questions);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      })

      setMediaStream(stream)
      if (videoRef.current) videoRef.current.srcObject = stream
      if (smallVideoRef.current) smallVideoRef.current.srcObject = stream

      setIsInterviewStarted(true) 
    } catch (error) {
      console.error('Error starting interview:', error)
      alert('Could not start interview. Please check permissions.')
    }
  }

  const startRecordingProcess = (stream: MediaStream) => {
    // ⚡ CHANGE 2: Ref ko reset karein
    mediaChunksRef.current = [];

    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'video/webm;codecs=vp8,opus',
    })

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        // ⚡ CHANGE 3: Direct Ref mein push karein (No State Delay)
        mediaChunksRef.current.push(event.data);
      }
    }

    // Note: onstop logic hum stopRecording function mein handle karenge promise ke zariye
    
    setRecorder(mediaRecorder)
    mediaRecorder.start(1000) // Collect chunks every 1 second
    setIsRecording(true)
    setIsStopped(false)
  }

  const stopRecording = async () => {
    if (!recorder || !isRecording || !sessionId) return

    setIsRecording(false)
    setIsUploading(true) 

    // Wait for REAL stop event
    await new Promise<void>((resolve) => {
        recorder.onstop = () => resolve();
        recorder.stop();
    });

    // Buffer safety
    await new Promise(r => setTimeout(r, 500));

    // Blob creation
    const blob = new Blob(mediaChunksRef.current, { type: 'video/webm' })
    
    console.log(`📹 Video Size: ${blob.size} bytes`);

    if (blob.size > 0) {
      const formData = new FormData()
      formData.append('video', blob, `question-${currentQuestion}.webm`)
      formData.append('questionId', `Q${currentQuestion}`) 
      formData.append('fieldId', fieldId)
      formData.append('sessionId', sessionId)
      
      // 🌟 NEW LOGIC: Backend ko question ka type aur details batayen
      const qType = currentQuestionData?.type || 'verbal';
      formData.append('questionType', qType);
      
      if (qType === 'coding') {
          // Agar coding question hai toh code editor ka data bhi sath bhejein
          formData.append('code', code); // Editor ka state variable
          formData.append('language', selectedLanguage); // Dropdown state
          formData.append('questionTitle', currentQuestionData.question);
          formData.append('questionDescription', currentQuestionData.description);
      }

      const token = localStorage.getItem('token')
      try {
        const response = await fetch('http://localhost:5000/api/interview/upload', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        })

        if (!response.ok) {
          const errorData = await response.json()
          console.error('Upload failed:', errorData)
          alert('Upload failed. Please try again.')
        } else {
            console.log(`✅ Video uploaded & ${qType === 'coding' ? 'Code' : 'Verbal'} Analysis started`)
        }
      } catch (error) {
        console.error('Error uploading video:', error)
      } finally {
        setIsUploading(false) 
        setIsStopped(true)
      }
    } else {
        console.error("❌ Blob size is 0, nothing recorded!");
        setIsUploading(false)
        setIsStopped(true)
    }
  }

  const handleFinishInterview = async () => {
    try {
        console.log("🏁 Finishing Interview...");
        const token = localStorage.getItem('token'); 
        
        const response = await axios.post('http://localhost:5000/api/interview/finish-interview', {
            sessionId: sessionId 
        }, {
            headers: { Authorization: `Bearer ${token}` }
        });

        console.log("✅ Report Generated:", response.data);
        router.push(`/results/${sessionId}`);

    } catch (error) {
        console.error(" Error finishing interview:", error);
        alert("Report generation failed. Please try again.");
    } 
  };

  const handleNextQuestion = async () => {
    if (currentQuestion < totalQuestions) {
      setCurrentQuestion(currentQuestion + 1)
      setCode('// Write your code here\n')
      setOutput('')
      setIsStopped(false)
      
      // Clear chunks ref
      mediaChunksRef.current = [];
      setIsRecording(false) 

    } else {
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop())
      }
      
      const token = localStorage.getItem('token')
      try {
        await fetch('http://localhost:5000/api/interview/count', {
          headers: { Authorization: `Bearer ${token}` },
        })
        window.dispatchEvent(new Event('dashboard-refresh'))
      } catch (error) {
        console.error('Error updating stats:', error)
      }

      alert('Interview completed! Redirecting to dashboard...')
      router.push('/dashboard')
    }
  }

  const runCode = async () => {
    setIsRunning(true)
    setOutput('Running...\n')

    try {
      const token = localStorage.getItem('token')
      const response = await fetch('http://localhost:5000/api/interview/run-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          code,
          language: selectedLanguage,
        }),
      })

      const data = await response.json()
      if (response.ok) {
        setOutput(data.output || data.result || 'Code executed successfully')
      } else {
        setOutput(`Error: ${data.error || data.message || 'Failed to execute code'}`)
      }
    } catch (error) {
      setOutput(`Error: ${error instanceof Error ? error.message : 'Failed to execute code.'}`)
    } finally {
      setIsRunning(false)
    }
  }

  useEffect(() => {
    return () => {
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [mediaStream])
  
  const currentQuestionData = (questions && questions.length > 0) 
  ? questions[currentQuestion - 1] 
  : { 
      question: "Welcome to PrepView AI", 
      description: "Click the 'Start Interview' button below to generate your AI-powered questions." 
    };

  const getMonacoLanguage = (lang: string) => {
    const mapping: { [key: string]: string } = {
      javascript: 'javascript',
      python: 'python',
      cpp: 'cpp',
      java: 'java',
      typescript: 'typescript',
      csharp: 'csharp',
    }
    return mapping[lang] || 'javascript'
  }

  return (
    <div className="min-h-screen bg-background text-text-primary">
      {/* Navbar */}
      <nav className="bg-white border-b border-border px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">P</span>
            </div>
            <span className="text-xl font-bold text-primary">PrepView</span>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-gray-600">
            Question {currentQuestion} of {questions.length || 5}  </span>
            <button
              onClick={() => router.push('/dashboard')}
              className="text-gray-600 hover:text-text-primary transition-colors"
            >
              Exit Interview
            </button>
          </div>
        </div>
      </nav>

      {/* Main Layout */}
      <div className="flex flex-col lg:flex-row h-[calc(100vh-80px)] pb-24">
        {/* Left Side */}
        <div className="w-full lg:w-1/2 flex flex-col p-6 space-y-6">
          <div className="bg-white rounded-xl p-6 border border-border shadow-md">
            <h3 className="text-xl font-bold mb-4 text-accent">Current Question</h3>
            <h4 className="text-lg font-semibold mb-2 text-text-primary">{currentQuestionData.question}</h4>
            <p className="text-gray-600">{currentQuestionData.description}</p>
          </div>
          <div className="bg-white rounded-xl border border-border overflow-hidden shadow-md">
            <div className="relative w-full aspect-video bg-gray-900">
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="w-full h-full object-cover"
              />
            </div>
          </div>
          <div className="bg-white rounded-xl p-8 border border-border flex items-center justify-center shadow-md">
            {/* AI Animation */}
            <div className="relative">
              <div className="w-48 h-48 rounded-full bg-gradient-to-br from-primary via-primary to-accent flex items-center justify-center shadow-2xl animate-pulse">
                <div className="w-40 h-40 rounded-full bg-white flex items-center justify-center">
                  <div className="text-6xl">🤖</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side (Monaco) */}
        <div className="w-full lg:w-1/2 flex flex-col p-6">
           <div className="bg-white rounded-xl border border-border overflow-hidden flex flex-col h-full shadow-md relative">
             {/* Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="text-lg font-semibold text-text-primary">Code Editor</h3>
              <div className="flex items-center space-x-3">
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className="px-3 py-1.5 border border-border rounded-lg text-sm bg-white"
                >
                  {languages.map((lang) => (
                    <option key={lang.value} value={lang.value}>{lang.label}</option>
                  ))}
                </select>
                <button
                  onClick={runCode}
                  disabled={isRunning}
                  className="bg-button-primary bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                >
                  {isRunning ? 'Running...' : 'Run'}
                </button>
              </div>
            </div>
            
            {/* Editor */}
            <div className="flex-1 relative" style={{ minHeight: '300px' }}>
              <MonacoEditor
                height="100%"
                language={getMonacoLanguage(selectedLanguage)}
                theme="vs"
                value={code}
                onChange={(value) => setCode(value || '')}
                options={{ minimap: { enabled: true }, fontSize: 14, automaticLayout: true }}
              />
              <div className="hidden lg:block absolute bottom-4 right-4 w-40 h-32 bg-gray-900 rounded-lg overflow-hidden border-2 border-accent shadow-xl z-50">
                <video
                  ref={smallVideoRef}
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-cover transform scale-x-[-1]" 
                />
              </div>
            </div>
            
            {/* Output */}
            <div className="border-t border-border">
              <div className="p-4 bg-gray-50">
                <h4 className="text-sm font-semibold text-text-primary mb-2">Output</h4>
                <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-green-400 min-h-[100px] max-h-[200px] overflow-y-auto">
                  <pre className="whitespace-pre-wrap">{output || 'Output will appear here...'}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-border px-6 py-4 shadow-lg z-20">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          {!isInterviewStarted ? (
            <button
              onClick={startInterview}
              className="bg-button-primary bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:opacity-90 w-full md:w-auto"
            >
              Start Interview
            </button>
          ) : (
            <div className="flex items-center justify-between w-full md:w-auto md:space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-gray-400'}`}></div>
                <span className="text-text-primary">
                  {isUploading ? 'Uploading & Analyzing...' : isRecording ? 'Recording...' : isStopped ? 'Stopped' : 'Paused'}
                </span>
              </div>
              
              {isRecording ? (
                <button
                  onClick={stopRecording}
                  className="bg-red-500 text-white px-8 py-3 rounded-lg font-semibold hover:opacity-90 mt-4 md:mt-0 w-full md:w-auto"
                >
                  Stop Recording
                </button>
              ) : isStopped ? (
                <button
                  onClick={currentQuestion < totalQuestions ? handleNextQuestion : handleFinishInterview}                 
                  disabled={isUploading}
                  className={`bg-button-primary bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:opacity-90 mt-4 md:mt-0 w-full md:w-auto ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {currentQuestion < totalQuestions ? 'Next Question' : 'Finish Interview'}
                </button>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}