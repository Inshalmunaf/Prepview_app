const express = require('express');
const router = express.Router();
const { PrismaClient } = require('@prisma/client');
const jwt = require('jsonwebtoken');

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

// Get CV
router.get('/', verifyToken, async (req, res) => {
  try {
    const cv = await prisma.cV.findUnique({
      where: { userId: req.userId },
    });

    if (!cv) {
      return res.status(404).json({ message: 'CV not found' });
    }

    res.json(cv);
  } catch (error) {
    console.error('Get CV error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Create CV
router.post('/', verifyToken, async (req, res) => {
  try {
    const cvData = req.body;

    // Check if CV already exists
    const existingCV = await prisma.cV.findUnique({
      where: { userId: req.userId },
    });

    if (existingCV) {
      // Update existing CV
      const updatedCV = await prisma.cV.update({
        where: { userId: req.userId },
        data: {
          personalInfo: cvData.personalInfo,
          summary: cvData.summary,
          skills: cvData.skills,
          projects: cvData.projects,
          education: cvData.education,
          experience: cvData.experience || null,
        },
      });

      return res.json(updatedCV);
    }

    // Create new CV
    const cv = await prisma.cV.create({
      data: {
        userId: req.userId,
        personalInfo: cvData.personalInfo,
        summary: cvData.summary,
        skills: cvData.skills,
        projects: cvData.projects,
        education: cvData.education,
        experience: cvData.experience || null,
      },
    });

    res.status(201).json(cv);
  } catch (error) {
    console.error('Create CV error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Update CV
router.put('/', verifyToken, async (req, res) => {
  try {
    const cvData = req.body;

    const cv = await prisma.cV.upsert({
      where: { userId: req.userId },
      update: {
        personalInfo: cvData.personalInfo,
        summary: cvData.summary,
        skills: cvData.skills,
        projects: cvData.projects,
        education: cvData.education,
        experience: cvData.experience || null,
      },
      create: {
        userId: req.userId,
        personalInfo: cvData.personalInfo,
        summary: cvData.summary,
        skills: cvData.skills,
        projects: cvData.projects,
        education: cvData.education,
        experience: cvData.experience || null,
      },
    });

    res.json(cv);
  } catch (error) {
    console.error('Update CV error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// API endpoint for Python AI model to access CV data via session/token
// This endpoint allows external AI services to fetch CV data using JWT token
router.get('/ai', verifyToken, async (req, res) => {
  try {
    const cv = await prisma.cV.findUnique({
      where: { userId: req.userId },
      select: {
        id: true,
        personalInfo: true,
        summary: true,
        skills: true,
        projects: true,
        education: true,
        experience: true,
        updatedAt: true,
      },
    });

    if (!cv) {
      return res.status(404).json({ 
        message: 'CV not found',
        error: 'CV_NOT_FOUND'
      });
    }

    // Return CV data in a format optimized for AI processing
    res.json({
      success: true,
      data: {
        personalInfo: cv.personalInfo,
        summary: cv.summary,
        skills: cv.skills, // Array of skill tags
        projects: cv.projects, // Array of projects with tech stack
        education: cv.education,
        experience: cv.experience,
      },
      metadata: {
        cvId: cv.id,
        lastUpdated: cv.updatedAt,
      }
    });
  } catch (error) {
    console.error('AI CV fetch error:', error);
    res.status(500).json({ 
      message: 'Internal server error',
      error: 'INTERNAL_ERROR'
    });
  }
});

module.exports = router;

