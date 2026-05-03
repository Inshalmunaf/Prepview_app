from prepview_engine.utils.common import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, InterviewChunk, FinalReport, InterviewSession
from prepview_engine.config.configuration import DatabaseConfig
import json
from typing import Dict, Any

class DatabaseConnector:
    def __init__(self, config:DatabaseConfig):
        """
        Initializes Database Connection.
        :param config: DatabaseConfig object (from ConfigurationManager)
        """
        self.db_url = config.get_sqlalchemy_uri()
        
        # Validation (Just in case config object empty ho)
        if not self.db_url:
            logger.critical(" Database URL is missing in the provided Config object")
            raise ValueError("Database URL missing")

        try:
            # Create Engine
            self.engine = create_engine(self.db_url, pool_pre_ping=True)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info(" [DB] Connected to PostgreSQL via Config Manager")
        except Exception as e:
            logger.exception(f" [DB] Connection Failed: {e}")
            raise e

    def get_db_session(self):
        return self.SessionLocal()
    
    def _sanitize_data(self, data):
        """
        Recursively converts NumPy types (float32, int64) to Python native types (float, int).
        """
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(i) for i in data]
        elif hasattr(data, 'item'): # Ye NumPy types ko pakar lega (float32 -> float)
            return data.item()
        else:
            return data
        
    def save_chunk_results(self, session_id: str, question_id: str, nlp_data: dict, cv_data: dict) -> bool:
        db = self.SessionLocal()
        try:
            # Check Session
            session_exists = db.query(InterviewSession).filter_by(session_id=session_id).first()
            if not session_exists:
                logger.error(f" [DB Error] Session ID {session_id} not found in DB!")
                return False

            clean_nlp = self._sanitize_data(nlp_data)
            clean_cv = self._sanitize_data(cv_data)

            new_chunk = InterviewChunk(
                session_id=session_id,
                question_id=question_id,

                # --- NLP Data ---
                nlp_full_json=clean_nlp, 
                transcript=clean_nlp.get('transcript', ''),
                speech_metrics=clean_nlp.get('speech_metrics', {}),
                linguistic_metrics=clean_nlp.get('linguistic_metrics', {}),
                phase1_score=float(clean_nlp.get('phase1_quality_score', 0.0)),
                prosodic_confidence=float(clean_nlp.get('prosodic_confidence', 0.0)),

                # --- CV Data ---
                cv_full_json=clean_cv, 
                head_movement=clean_cv.get('head_movement', {}),
                eye_gaze=clean_cv.get('eye_gaze', {}),
                facial_expression=clean_cv.get('facial_expression', {}),
                cv_score=float(clean_cv.get('cv_score', 0.0)),

                # 🌟 CODE & PROCTORING DEFAULTS (For Verbal Analysis)
                original_technical_score=0,
                score_with_penalties=0,
                proctoring_results={}  # SQLAlchemy naturally converts empty dict to JSON
            )

            db.add(new_chunk)
            db.commit()
            db.refresh(new_chunk)
            
            logger.info(f" Verbal Chunk saved successfully: Session={session_id} | Q={question_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f" Failed to save verbal chunk: {e}", exc_info=True)
            return False
        finally:
            db.close()

    # ==================================================
    # 2. FUNCTION FOR CODE ANALYSIS & PROCTORING
    # ==================================================
    def save_code_results(self, session_id: str, question_id: str, code_data: dict) -> bool:
        db = self.SessionLocal()
        try:
            # Check Session
            session_exists = db.query(InterviewSession).filter_by(session_id=session_id).first()
            if not session_exists:
                logger.error(f" [DB Error] Session ID {session_id} not found in DB!")
                return False

            # Extract Code & Proctoring Scores
            tech_score = code_data.get("original_technical_score", 0)
            score_with_penalties = code_data.get("score_with_penalties", 0)
            proctoring_raw = code_data.get("proctoring_results", {})

            new_chunk = InterviewChunk(
                session_id=session_id,
                question_id=question_id,

                # --- CODE & PROCTORING DATA ---
                original_technical_score=tech_score,
                score_with_penalties=score_with_penalties,
                proctoring_results=proctoring_raw,

                # 🌟 NLP & CV DEFAULTS (For Code Analysis)
                nlp_full_json={},
                transcript="",
                speech_metrics={},
                linguistic_metrics={},
                phase1_score=0.0,
                prosodic_confidence=0.0,
                
                cv_full_json={},
                head_movement={},
                eye_gaze={},
                facial_expression={},
                cv_score=0.0
            )

            db.add(new_chunk)
            db.commit()
            db.refresh(new_chunk)
            
            logger.info(f" Code DB Save Successful! Session={session_id} | Q={question_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f" DB Save Failed for code chunk {question_id}: {e}", exc_info=True)
            return False
        finally:
            db.close()
        
    def fetch_session_chunks(self, session_id):
        db = self.SessionLocal()
        try:
            chunks = db.query(InterviewChunk).filter_by(session_id=session_id).all()
            logger.info(f"ℹ️ Fetched {len(chunks)} chunks for session {session_id}")
            return chunks
        except Exception as e:
            logger.error(f" Error fetching chunks: {e}")
            return []
        finally:
            db.close()

    def save_final_report(self, session_id, user_id, nlp_agg, cv_agg, code_agg, feedback_text):
        db = self.SessionLocal()
        try:
            # Check agar is session ki report pehle se mojud hai
            existing_report = db.query(FinalReport).filter_by(session_id=session_id).first()
            
            if existing_report:
                # Agar mojud hai, toh usko update karein (Taakay Unique Constraint error na aaye)
                existing_report.nlp_aggregate = nlp_agg
                existing_report.cv_aggregate = cv_agg
                existing_report.code_aggregate = code_agg  # 💻 Naya Column
                existing_report.ai_feedback = feedback_text
                logger.info(f" Final Report updated for Session: {session_id}")
            else:
                # Agar nahi hai, toh nayi report create karein
                new_report = FinalReport(
                    session_id=session_id,
                    userId=user_id,
                    nlp_aggregate=nlp_agg,
                    cv_aggregate=cv_agg,
                    code_aggregate=code_agg,  
                    ai_feedback=feedback_text
                )
                db.add(new_report)
                logger.info(f" Final Report created for Session: {session_id}")
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f" Failed to save final report: {e}", exc_info=True)
            return False
        finally:
            db.close()