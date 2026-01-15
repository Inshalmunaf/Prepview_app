'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

// 👇 Aapke Components Imports
import MetricCard from '@/components/MetricCard'; 
import Section from '@/components/Section';
import TranscriptBox from '@/components/TranscriptBox'; 

export default function ResultPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
           setError("User login nahi hai");
           return;
        }

        // Backend API Call
        const res = await fetch(`http://localhost:5000/api/interview/results/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Report fetch failed");
        
        const data = await res.json();
        setReport(data.data); 

      } catch (err) {
        console.error("Error:", err);
        setError("Report load nahi ho saki.");
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      fetchReport();
    }
  }, [sessionId]);

  // Loading State
  if (loading) return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
       <div className="text-xl font-semibold text-blue-600 animate-pulse">
          📊 Generating Analysis Report...
       </div>
    </div>
  );

  // Error State
  if (error || !report) return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
       <div className="text-red-500 font-bold text-lg">{error || "Report Not Found"}</div>
    </div>
  );

  // 👇 DATA PARSING
  const nlp = typeof report.nlp_aggregate === 'string' ? JSON.parse(report.nlp_aggregate) : report.nlp_aggregate;
  const cv = typeof report.cv_aggregate === 'string' ? JSON.parse(report.cv_aggregate) : report.cv_aggregate;

  // Values formatting helpers
  const fillerPercentage = nlp?.avg_filler_rate ? (nlp.avg_filler_rate * 100).toFixed(1) : "0";
  const eyeContact = cv?.avg_eye_contact ? cv.avg_eye_contact.toFixed(1) : "0";
  const nervousLevel = cv?.avg_nervousness ? cv.avg_nervousness.toFixed(1) : "0";

  return (
    <div className="min-h-screen bg-gray-50 p-8 text-slate-800">
      <div className="max-w-6xl mx-auto space-y-10">
        
        {/* Header */}
        <div className="flex justify-between items-end border-b pb-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">Interview Performance Report</h1>
              <p className="text-slate-500 mt-1">AI-powered evaluation of your interview performance</p>
            </div>
            <button 
              onClick={() => router.push('/dashboard')} 
              className="bg-slate-900 text-white px-5 py-2 rounded-lg hover:bg-slate-700 transition shadow-sm"
            >
                Back to Dashboard
            </button>
        </div>

        {/* 1. Overall Performance Section */}
        <Section title="Overall Performance">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MetricCard 
                    label="Communication Quality" 
                    value={`${nlp?.avg_nlp_score?.toFixed(0) || 0}/100`} 
                />
                <MetricCard
                    label="Visual Presence Score" 
                    value={`${cv?.avg_cv_score?.toFixed(0) || 0}/100`} 
                />
                <MetricCard 
                    label="Weakest Response" 
                    value={nlp?.weakest_answer_id || "N/A"} 
                />
            </div>
        </Section>

        {/* 2. Verbal & Language Analysis */}
        <Section title="Verbal & Language Analysis">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <MetricCard label="Speaking Speed" value={`${nlp?.avg_wpm?.toFixed(1) || 0} WPM`} />
                <MetricCard label="Filler Word Usage" value={`${fillerPercentage}%`} />
                <MetricCard label="Lowest Combined Score" value={`${nlp?.lowest_combined_score?.toFixed(1) || 0}/100`} />
                <MetricCard label="Dominant Mood" value={cv?.dominant_mood || "Neutral"} />
            </div>

            {/* Transcript Preview Box */}
            <TranscriptBox transcript={nlp?.transcript_sample || "No transcript available for this session."} />
        </Section>

        {/* 3. Visual Presence Analysis */}
        <Section title="Visual Presence Analysis">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MetricCard label="Eye Contact Consistency" value={`${eyeContact}%`} />
                <MetricCard label="Nervousness Level" value={`${nervousLevel}%`} />
                <MetricCard label="Emotional State" value={cv?.dominant_mood || "Neutral"} />
            </div>
        </Section>

        {/* 4. AI Feedback Section */}
        <Section title="AI Interview Feedback">
            <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
                <div className="prose max-w-none text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {report.ai_feedback ? report.ai_feedback : (
                        <p className="text-gray-400 italic">No detailed feedback available.</p>
                    )}
                </div>
            </div>
        </Section>

      </div>
    </div>
  );
}