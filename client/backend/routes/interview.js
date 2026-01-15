const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { PrismaClient } = require('@prisma/client');
const jwt = require('jsonwebtoken');
const { exec } = require('child_process');
const util = require('util');
const axios = require('axios');
const aiEngine = require('../utils/aiEngine.js'); 

const execPromise = util.promisify(exec);
const prisma = new PrismaClient();

// Middleware to verify token
const verifyToken = (req, res, next) => {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return res.status(401).json({ message: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(
      token,
      process.env.JWT_SECRET || 'your-secret-key-change-in-production'
    );
    req.userId = decoded.userId;
    next();
  } catch (error) {
    return res.status(401).json({ message: 'Invalid token' });
  }
};

// Configure multer for video uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    // Ensure absolute path for compatibility with Python
    const uploadsDir = path.join(__dirname, '../../uploads/videos'); 
    if (!fs.existsSync(uploadsDir)) {
      fs.mkdirSync(uploadsDir, { recursive: true });
    }
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    const userId = req.userId;
    const questionId = req.body.questionId || 'unknown';
    // Clean filename logic
    const uniqueSuffix = `${Date.now()}-${Math.round(Math.random() * 1E9)}`;
    const ext = path.extname(file.originalname) || '.webm';
    cb(null, `${userId}_${questionId}_${uniqueSuffix}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 500 * 1024 * 1024 }, // 500MB limit
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('video/')) {
      cb(null, true);
    } else {
      cb(new Error('Only video files are allowed'));
    }
  },
});

// ==========================================
// 1. CREATE SESSION (With Detailed CV Fetch)
// ==========================================
router.post('/session', verifyToken, async (req, res) => {
  try {
    const { fieldId } = req.body;
    console.log(`👉 Session Request - User: ${req.userId}, Field: ${fieldId}`);

    // ---------------------------------------------------------
    // 👇 STEP A: Fetch User's CV Data (Summary, Skills, Projects) 🗄️
    // ---------------------------------------------------------
    const userWithCV = await prisma.user.findUnique({
      where: { id: req.userId },
      include: {
        // Hum man kar chal rahay hain ke relation ka naam 'cv' hai
        cv: {
          select: {
            summary: true,
            skills: true,
            projects: true
          }
        }
      }
    });

    if (!userWithCV) {
      return res.status(404).json({ message: "User not found" });
    }

    // Data Format karna (AI ke liye)
    // Agar CV nahi bani hui, toh empty object rakhein
    const cvData = userWithCV.cv ? {
      summary: userWithCV.cv.summary || "Not provided",
      skills: userWithCV.cv.skills || [],
      projects: userWithCV.cv.projects || []
    } : { summary: "No CV found", skills: [], projects: [] };

    console.log("📄 CV Data Fetched:", cvData ? "Yes" : "No");
    console.log(cvData)
    // ---------------------------------------------------------
    // 👇 STEP B: Generate Questions (AI) 🧠
    // ---------------------------------------------------------
    console.log("🤖 Generating AI Questions...");
    
    // Ab hum poora Object bhej rahay hain (Summary + Skills + Projects)
    const questions = await aiEngine.generateQuestions(cvData, fieldId || 'General');
    
    console.log(`✅ Generated ${questions.length} Questions`);

    // ---------------------------------------------------------
    // 👇 STEP C: Create Session (DB) 💾
    // ---------------------------------------------------------
    const generatedSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const session = await prisma.interviewSession.create({
      data: {
        session_id: generatedSessionId,
        userId: req.userId,
        fieldid: fieldId || 'General',
      },
    });

    // ---------------------------------------------------------
    // 👇 STEP D: Send Response 🚀
    // ---------------------------------------------------------
    res.json({
      message: 'Interview session created',
      sessionId: session.session_id,
      fieldId: session.fieldid,
      questions: questions 
    });

  } catch (error) {
    console.error('Create session error:', error);
    res.status(500).json({ message: 'Error creating session', error: error.message });
  }
});

// ==========================================
// 2. UPLOAD VIDEO & TRIGGER PYTHON AI
// ==========================================
router.post('/upload', verifyToken, upload.single('video'), async (req, res) => {
  try {
    // 1. Validation
    if (!req.file) {
      return res.status(400).json({ message: 'No video file uploaded' });
    }

    const { questionId, sessionId } = req.body;
    if (!sessionId) {
      return res.status(400).json({ message: 'Session ID is required' });
    }

    // 2. File Path Sahi Karna (Critical Step for Windows) 
    // Windows par path 'C:\User\...' ata hai jo JSON mein error deta hai.
    // Hum isay Forward Slashes '/' mein convert kar denge.
    let videoAbsolutePath = path.resolve(req.file.path);
    videoAbsolutePath = videoAbsolutePath.replace(/\\/g, '/'); 

    console.log(`[Node]  Video Saved at: ${videoAbsolutePath}`);
    console.log(`[Node]  Handshaking with Python AI for Q: ${questionId}`);

    // 3. PYTHON API CALL (Fire & Forget) 
    // Hum 'await' nahi lagayenge taakay User ko wait na karna pare.
    axios.post('http://localhost:8000/analyze_chunk', {
      session_id: sessionId,
      question_id: questionId,
      video_file_path: videoAbsolutePath
    })
    .then(pyRes => {
      console.log(`[Python Success]  Status: ${pyRes.data.status}`);
    })
    .catch(err => {
      // Agar Python band hai, toh Node crash nahi hona chahiye
      console.error(`[Python Failed]  Error: ${err.message}`);
      if (err.code === 'ECONNREFUSED') {
        console.error(" Tip: Check if 'python app.py' is running on port 8000");
      }
    });

    // 4. Response to Frontend (React)
    // Frontend ko bas ye bata do ke upload ho gaya, baqi kaam peeche ho raha hai
    res.json({
      message: 'Video uploaded successfully. AI analysis started in background.',
      sessionId: sessionId,
      filename: req.file.filename,
      pythonTriggered: true
    });

  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ message: 'Error uploading video', error: error.message });
  }
});




// ==========================================
// 🏁 FINISH INTERVIEW & GENERATE REPORT
// ==========================================
router.post('/finish-interview', verifyToken, async (req, res) => {
  try {
    const { sessionId } = req.body;

    if (!sessionId) {
      return res.status(400).json({ message: 'Session ID is required' });
    }

    console.log(`[Node] 🏁 Finishing Interview for Session: ${sessionId}`);

  

    // Call Python API to Generate Report
    // Yahan hum 'await' use karenge kyunki User report ka wait kar raha hai
    const pythonResponse = await axios.post('http://localhost:8000/generate_finalreport', {
      session_id: sessionId,
      user_id: req.userId // Token se nikala hua secure User ID
    });

    console.log("[Node] ✅ Report Generated Successfully!");

    // Frontend ko data wapis bhejein
    res.json({
      message: 'Report generated successfully',
      data: pythonResponse.data 
    });

  } catch (error) {
    console.error('[Node] ❌ Report Generation Failed:', error.message);
    
    // Agar Python ne error diya
    if (error.response) {
      return res.status(error.response.status).json(error.response.data);
    }
    
    res.status(500).json({ message: 'Failed to generate report', error: error.message });
  }
});
module.exports = router;
// ==========================================
// 3. GET SESSION RESULTS (From DB)
// ==========================================
router.get('/results/:sessionId', verifyToken, async (req, res) => {
  try {
    const { sessionId } = req.params;

    // Fetch Chunks directly from Database (Populated by Python)
    const chunks = await prisma.interviewChunk.findMany({
      where: { session_id: sessionId },
      orderBy: { question_id: 'asc' }
    });

    res.json({ sessionId, chunks });
  } catch (error) {
    console.error('Get results error:', error);
    res.status(500).json({ message: 'Error fetching results' });
  }
});

// ==========================================
// 4. CODE EXECUTION (No Changes Needed)
// ==========================================
router.post('/run-code', verifyToken, async (req, res) => {
  try {
    const { code, language } = req.body;
    if (!code || !language) return res.status(400).json({ message: 'Code/Lang required' });

    const tempDir = path.join(__dirname, '../temp');
    if (!fs.existsSync(tempDir)) fs.mkdirSync(tempDir, { recursive: true });

    let command = '';
    let tempFile = '';
    const timestamp = Date.now();

    switch (language) {
      case 'javascript':
        tempFile = path.join(tempDir, `code-${timestamp}.js`);
        fs.writeFileSync(tempFile, code);
        command = `node "${tempFile}"`;
        break;
      case 'python':
        tempFile = path.join(tempDir, `code-${timestamp}.py`);
        fs.writeFileSync(tempFile, code);
        command = `python "${tempFile}"`;
        break;
      // ... Add other languages as needed
      default:
        return res.status(400).json({ message: 'Unsupported language' });
    }

    try {
      const { stdout, stderr } = await execPromise(command, { timeout: 10000 });
      if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile);
      res.json({ output: stdout || stderr, result: stdout, error: stderr || null });
    } catch (execError) {
      if (fs.existsSync(tempFile)) fs.unlinkSync(tempFile);
      res.json({ output: execError.stderr || execError.message, error: execError.message });
    }
  } catch (error) {
    res.status(500).json({ message: 'Execution error', error: error.message });
  }
});

// ==========================================
// 5. USER STATS ROUTES
// ==========================================
router.get('/count', verifyToken, async (req, res) => {
  try {
    // ✅ Schema Update: userId (camelCase) is correct based on schema
    const uniqueSessions = await prisma.interviewSession.groupBy({
      by: ['session_id'],
      where: { userId: req.userId },
    });
    res.json({ count: uniqueSessions.length });
  } catch (error) {
    res.status(500).json({ message: 'Internal server error' });
  }
});

router.get('/sessions', verifyToken, async (req, res) => {
  try {
    const sessions = await prisma.interviewSession.findMany({
      where: { userId: req.userId },
      orderBy: { createdAt: 'desc' }, // ✅ Schema uses createdAt
      include: { 
        chunks: true // Optional: Include chunks data if needed
      }
    });
    res.json(sessions);
  } catch (error) {
    res.status(500).json({ message: 'Internal server error' });
  }
});

module.exports = router;