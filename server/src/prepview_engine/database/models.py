from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON 
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# ==========================================
# 1. USER TABLE (ReadOnly access for Python)
# ==========================================
class User(Base):
    __tablename__ = 'users'  # ✅ Matches Prisma @@map("users")

    id = Column(String, primary_key=True)  # CUID String form Prisma
    username = Column(String)
    email = Column(String)
    # password_hash ki zaroorat nahi yahan

    # Relations
    cv = relationship("CV", back_populates="user", uselist=False) # One-to-One
    sessions = relationship("InterviewSession", back_populates="user")
    reports = relationship("FinalReport", back_populates="user")


# ==========================================
# 2. CV / RESUME TABLE (Added as requested)
# ==========================================
class CV(Base):
    __tablename__ = 'cvs'  # ✅ Matches Prisma @@map("cvs")

    id = Column(String, primary_key=True)
    
    # Foreign Key (One-to-One with User)
    userId = Column(String, ForeignKey('users.id'), unique=True)

    # JSON Data Fields (Matching Prisma Schema)
    personalInfo = Column(JSON)      # { fullName, email, ... }
    summary = Column(Text, nullable=True)
    skills = Column(JSON)            # Array of strings
    projects = Column(JSON)          # Array of objects
    education = Column(JSON)         # Array of objects
    experience = Column(JSON, nullable=True)
    
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="cv")


# ==========================================
# 3. INTERVIEW SESSION
# ==========================================
class InterviewSession(Base):
    __tablename__ = 'interview_sessions'  # ✅ Matches Prisma @@map("interview_sessions")

    # Prisma: session_id String @id @unique
    session_id = Column(String, primary_key=True) 
    
    # Foreign Keys
    userId = Column(String, ForeignKey('users.id')) 
    fieldid = Column(String) 
    
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    user = relationship("User", back_populates="sessions")
    chunks = relationship("InterviewChunk", back_populates="session")
    report = relationship("FinalReport", back_populates="session")

# ==========================================
# 4. INTERVIEW CHUNKS (Analysis Data)
# ==========================================
class InterviewChunk(Base):
    __tablename__ = 'interview_chunks'  # ✅ Matches Prisma @@map("interview_chunks")

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to Session
    session_id = Column(String, ForeignKey('interview_sessions.session_id'))
    question_id = Column(String) # e.g. "Q1"

    # 🧠 NLP Data (Direct JSON storage)
    nlp_full_json = Column(JSON, nullable=True)       
    transcript = Column(Text, nullable=True)
    speech_metrics = Column(JSON, nullable=True)      
    linguistic_metrics = Column(JSON, nullable=True)  
    phase1_score = Column(Float, nullable=True)
    prosodic_confidence = Column(Float, nullable=True)

    # 👁️ CV/Video Data
    cv_full_json = Column(JSON, nullable=True)
    head_movement = Column(JSON, nullable=True)
    eye_gaze = Column(JSON, nullable=True)
    facial_expression = Column(JSON, nullable=True)
    cv_score = Column(Float, nullable=True)

    # 💻 CODE & PROCTORING DATA (NEW)
    original_technical_score = Column(Float, nullable=True)
    score_with_penalties = Column(Float, nullable=True)
    proctoring_results = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    session = relationship("InterviewSession", back_populates="chunks")


# ==========================================
# 5. FINAL REPORT (Summary)
# ==========================================
class FinalReport(Base):
    __tablename__ = 'final_reports'  # ✅ Matches Prisma @@map("final_reports")

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Links
    session_id = Column(String, ForeignKey('interview_sessions.session_id'), unique=True)
    userId = Column(String, ForeignKey('users.id'))

    # AI Output
    nlp_aggregate = Column(JSON, nullable=True)
    cv_aggregate = Column(JSON, nullable=True)
    
    # 💻 CODE & PROCTORING AGGREGATE (NEW)
    code_aggregate = Column(JSON, nullable=True)
    
    ai_feedback = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    session = relationship("InterviewSession", back_populates="report")
    user = relationship("User", back_populates="reports")