from prepview_engine.utils.common import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, InterviewChunk, FinalReport, InterviewSession
from prepview_engine.config.configuration import DatabaseConfig


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
        
    def save_chunk_results(self, session_id, question_id, nlp_data, cv_data):
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

                # NLP Data
                nlp_full_json=clean_nlp, # Clean data save karo
                transcript=clean_nlp.get('transcript', ''),
                speech_metrics=clean_nlp.get('speech_metrics', {}),
                linguistic_metrics=clean_nlp.get('linguistic_metrics', {}),
                phase1_score=float(clean_nlp.get('phase1_quality_score', 0.0)),
                prosodic_confidence=float(clean_nlp.get('confidence', 0.0)),

                # CV Data
                cv_full_json=clean_cv, # Clean data save karo
                head_movement=clean_cv.get('head_movement', {}),
                eye_gaze=clean_cv.get('eye_gaze', {}),
                facial_expression=clean_cv.get('facial_expression', {}),
                cv_score=float(clean_cv.get('cv_score', 0.0))
            )

            db.add(new_chunk)
            db.commit()
            db.refresh(new_chunk)
            
            logger.info(f" Chunk saved: Session={session_id} | Q={question_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f" Failed to save chunk: {e}", exc_info=True)
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

    def save_final_report(self, session_id, user_id, nlp_agg, cv_agg, feedback_text):
        db = self.SessionLocal()
        try:
            new_report = FinalReport(
                session_id=session_id,
                userId=user_id,
                nlp_aggregate=nlp_agg,
                cv_aggregate=cv_agg,
                ai_feedback=feedback_text
            )
            
            db.add(new_report)
            db.commit()
            logger.info(f" Final Report saved for Session: {session_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f" Failed to save report: {e}", exc_info=True)
            return False
        finally:
            db.close()