import axios from 'axios';

// Python Backend URL (Port 8000)
const AI_API_URL = "http://localhost:8000";

export const aiService = {
  
  // 1. Analyze Chunk (Jab aik sawal ka jawab record ho jaye)
  analyzeChunk: async (sessionId, questionId, videoPath) => {
    try {
      console.log(`📡 Calling AI Analysis for Question: ${questionId}`);
      
      const payload = {
        session_id: sessionId,
        question_id: questionId,
        video_file_path: videoPath // ⚠️ Note: Ye File ka PATH mangta hai, File object nahi
      };

      const response = await axios.post(`${AI_API_URL}/analyze_chunk`, payload);
      console.log(" AI Analysis Started:", response.data);
      return response.data;
    } catch (error) {
      console.error(" AI Analysis Failed:", error);
      throw error;
    }
  },

  // 2. Generate Final Report (Jab interview khatam ho)
  generateFinalReport: async (sessionId, userId) => {
    try {
      console.log(` Requesting Final Report for Session: ${sessionId}`);
      
      const payload = {
        session_id: sessionId,
        user_id: userId
      };

      const response = await axios.post(`${AI_API_URL}/generate_finalreport`, payload);
      console.log(" Report Generation Started:", response.data);
      return response.data;
    } catch (error) {
      console.error(" Report Generation Failed:", error);
      throw error;
    }
  }
};