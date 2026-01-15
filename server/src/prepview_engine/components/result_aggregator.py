import numpy as np
from typing import Dict, Any, List
from collections import Counter
from prepview_engine.utils.common import logger

class ResultAggregator:
    def __init__(self, db_connector):
        self.db = db_connector
        # Emoji removed below
        logger.info("Result Aggregator Initialized (with DB connection).")

    # ==========================================
    #  HELPER: DATA CLEANING
    # ==========================================
    def _sanitize(self, value):
        if isinstance(value, (np.integer, int)): return int(value)
        elif isinstance(value, (np.floating, float)): return round(float(value), 2)
        elif isinstance(value, (np.ndarray, list)): return [self._sanitize(x) for x in value]
        elif isinstance(value, dict): return {k: self._sanitize(v) for k, v in value.items()}
        return value

    def _safe_mean(self, values: List[float]) -> float:
        if not values: return 0.0
        return round(float(np.mean(values)), 2)

    # ==========================================
    #  MAIN FUNCTION
    # ==========================================
    def aggregate_session(self, session_id: str) -> Dict[str, Any]:
        """
        Fetches chunks internally using session_id and produces a summary.
        Now compatible with SQLAlchemy Objects.
        """
        
        # 1. Fetch Data from DB internally
        logger.info(f"Fetching chunks internally for Session: {session_id}")
        
        session_chunks = self.db.fetch_session_chunks(session_id)

        if not session_chunks:
            logger.warning(f"No chunks found for Session ID: {session_id}")
            return {}

        logger.info(f"Aggregating {len(session_chunks)} chunks...")

        # 2. Storage Containers
        # NLP
        wpms, filler_rates, nlp_scores = [], [], []
        # CV
        cv_scores, eye_contacts, nervousness_scores, dominant_moods = [], [], [], []

        # Weakest Link Logic
        lowest_combined_score = 101.0
        worst_transcript_snippet = "No transcript available."
        worst_question_id = "N/A"

        # 3. Iterate & Extract 
        for chunk in session_chunks:
            
            # --- Scores (Handling Attributes) ---
            n_score = getattr(chunk, "phase1_score", 0) or 0
            nlp_scores.append(n_score)

            c_score = getattr(chunk, "cv_score", 0) or 0 
            cv_scores.append(c_score)

            # --- Detailed Metrics (Handling JSON Fields) ---
            # DB se JSON field "None" aasakti hai, isliye "or {}" zaroori hai
            
            # 1. Speech
            speech = getattr(chunk, "speech_metrics", {}) or {}
            wpms.append(speech.get("speech_rate_wpm", 0))
            filler_rates.append(speech.get("filler_rate", 0))

            # 2. Eye Gaze
            eye_data = getattr(chunk, "eye_gaze", {}) or {}
            eye_contacts.append(eye_data.get("eye_contact_percentage", 0))

            # 3. Facial Expressions
            face_data = getattr(chunk, "facial_expression", {}) or {}
            dominant_moods.append(face_data.get("dominant_mood", "neutral"))
            
            nerv_data = face_data.get("nervousness_analysis") or {}
            nervousness_scores.append(nerv_data.get("total_concerned_percentage", 0))

            # --- 4. Weakest Answer Logic (Combined Score) ---
            if n_score > 0 and c_score > 0:
                current_combined = (n_score + c_score) / 2
            else:
                current_combined = n_score if n_score > 0 else c_score

            # Logic to find the worst answer
            if current_combined > 0 and current_combined < lowest_combined_score:
                lowest_combined_score = current_combined
                
                # Attribute Access
                worst_question_id = getattr(chunk, "question_id", "Unknown")
                raw_text = getattr(chunk, "transcript", "") or ""
                
                worst_transcript_snippet = raw_text[:800] if raw_text else "Audio unclear."

        # 5. Final Calculations
        final_mood = "neutral"
        if dominant_moods:
            # Most common mood nikalna
            final_mood = Counter(dominant_moods).most_common(1)[0][0]

        summary = {
            "nlp_aggregate": {
                "avg_nlp_score": self._safe_mean(nlp_scores),
                "avg_wpm": self._safe_mean(wpms),
                "avg_filler_rate": self._safe_mean(filler_rates),
                
                # Context info for LLM
                "weakest_answer_id": worst_question_id,
                "lowest_combined_score": round(lowest_combined_score, 2),
                "transcript_sample": worst_transcript_snippet
            },
            
            "cv_aggregate": {
                "avg_cv_score": self._safe_mean(cv_scores),
                "avg_eye_contact": self._safe_mean(eye_contacts),
                "avg_nervousness": self._safe_mean(nervousness_scores),
                "dominant_mood": final_mood
            }
        }

        return self._sanitize(summary)