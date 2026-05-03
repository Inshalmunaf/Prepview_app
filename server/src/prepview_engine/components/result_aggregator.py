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
    def aggregate_session(self, session_id: str) -> dict:
        """
        Aggregates NLP, CV, and Code chunks into a detailed summary.
        Returns the dictionary so it can be saved by another function.
        """
        try:
            # 1. Fetch Data from DB internally
            logger.info(f"Fetching chunks internally for Session: {session_id}")
            
            session_chunks = self.db.fetch_session_chunks(session_id)

            if not session_chunks:
                logger.warning(f"No chunks found for Session ID: {session_id}")
                return {}


            # --- NLP & CV Lists ---
            nlp_scores, wpms, filler_rates = [], [], []
            lexical_richnesses, repetition_ratios, semantic_instabilities, aux_verb_ratios = [], [], [], []
            cv_scores, eye_contacts, nervousness_scores = [], [], []
            total_emotions = {"happy": 0.0, "neutral": 0.0, "surprised": 0.0, "concerned": 0.0}

            # --- Weakest Answer Trackers ---
            lowest_combined_score = float('inf')
            worst_question_id = None
            worst_transcript_snippet = ""

            # --- Code & Proctoring Trackers ---
            total_penalty_score = 0
            coding_question_count = 0
            cheating_incidents = []

            # Loop through all chunks once
            for chunk in session_chunks:
                
                # ==========================================
                # 1. VERBAL EXTRACTION (NLP & CV)
                # ==========================================
                if chunk.phase1_score is not None and chunk.phase1_score > 0:
                    
                    nlp_val = chunk.phase1_score
                    cv_val = chunk.cv_score or 0.0
                    
                    nlp_scores.append(nlp_val)
                    cv_scores.append(cv_val)

                    # Metrics Extract (Assuming DB fields match these exact keys)
                    if chunk.speech_metrics:
                        wpms.append(chunk.speech_metrics.get("speech_rate_wpm", 0))
                        filler_rates.append(chunk.speech_metrics.get("filler_rate", 0))
                    if chunk.linguistic_metrics:
                        # Direct values extract karein
                        lexical_richnesses.append(chunk.linguistic_metrics.get("lexical_richness", 0.0))
                        repetition_ratios.append(chunk.linguistic_metrics.get("repetition_ratio", 0.0))
                        semantic_instabilities.append(chunk.linguistic_metrics.get("semantic_instability", 0.0))
                        
                        # Nested value (aux_verb_ratio) extract karne ke liye safe approach
                        synth_uncertainty = chunk.linguistic_metrics.get("syntactic_uncertainty", {})
                        aux_verb_ratios.append(synth_uncertainty.get("aux_verb_ratio", 0.0))
                    if chunk.eye_gaze:
                        eye_contacts.append(chunk.eye_gaze.get("eye_contact_percentage", 0))
                    if chunk.facial_expression:
                    # DB se emotion_distribution wali dictionary nikalen
                        nervousness_analysis = chunk.facial_expression.get("nervousness_analysis", {})
                        nervousness_scores.append(nervousness_analysis.get("total_concerned_percentage", 0.0))
                        emotion_dist = chunk.facial_expression.get("emotion_distribution", {})
                        
                        # Har mood ki value ko jama karein (safe float casting ke sath)
                        total_emotions["happy"] += float(emotion_dist.get("happy", 0.0))
                        total_emotions["neutral"] += float(emotion_dist.get("neutral", 0.0))
                        total_emotions["surprised"] += float(emotion_dist.get("surprised", 0.0))
                        total_emotions["concerned"] += float(emotion_dist.get("concerned", 0.0))

                    # Find Weakest Answer
                    combined_score = (nlp_val + cv_val) / 2
                    if combined_score < lowest_combined_score:
                        lowest_combined_score = combined_score
                        worst_question_id = chunk.question_id
                        worst_transcript_snippet = (chunk.transcript or "")[:150] + "..."

                # ==========================================
                # 2. CODE & PROCTORING EXTRACTION
                # ==========================================
                proc_results = chunk.proctoring_results or {}
                if "is_cheating_suspected" in proc_results:
                    coding_question_count += 1
                    total_penalty_score += (chunk.score_with_penalties or 0)

                    if proc_results.get("is_cheating_suspected") == True:
                        cheating_incidents.append({
                            "question_id": chunk.question_id,
                            "reasons": proc_results.get("reasons", [])
                        })

            # ==========================================
            # 3. FINAL CALCULATIONS
            # ==========================================
            if lowest_combined_score == float('inf'):
                lowest_combined_score = 0.0

            # Default mood
            dominant_mood = "Neutral"

            # Agar saari values 0 nahi hain (Yani verbal chunks thay)
            if sum(total_emotions.values()) > 0:
                # max() function dictionary mein se sab se bari value wali key nikal layega
                max_emotion = max(total_emotions, key=total_emotions.get) 
                
                # Capitalize the first letter (e.g., "happy" -> "Happy")
                dominant_mood = max_emotion.capitalize()

            avg_code = total_penalty_score / coding_question_count if coding_question_count > 0 else 0.0

            # ==========================================
            # 4. BUILD REQUESTED DICTIONARIES
            # ==========================================
            summary = {
                "nlp_aggregate": {
                    "avg_nlp_score": self._safe_mean(nlp_scores),
                    "avg_wpm": self._safe_mean(wpms),
                    "avg_filler_rate": self._safe_mean(filler_rates),
                    "avg_lexical_richness": self._safe_mean(lexical_richnesses),
                    "avg_repetition_ratio": self._safe_mean(repetition_ratios),
                    "avg_uncertainty": self._safe_mean(aux_verb_ratios),
                    "avg_semantic_instability": self._safe_mean(semantic_instabilities),
                    # Context info for LLM
                    "weakest_answer_id": worst_question_id,
                    "lowest_combined_score": round(lowest_combined_score, 2),
                    "transcript_sample": worst_transcript_snippet
                },
                
                "cv_aggregate": {
                    "avg_cv_score": self._safe_mean(cv_scores),
                    "avg_eye_contact": self._safe_mean(eye_contacts),
                    "avg_nervousness": self._safe_mean(nervousness_scores),
                    "dominant_mood": dominant_mood
                },

                "code_aggregate": {
                    "avg_score_with_penalties": round(avg_code, 2),
                    "total_coding_questions_attempted": coding_question_count,
                    "cheating_incidents": cheating_incidents
                }
            }

            return self._sanitize(summary)

        except Exception as e:
            logger.error(f" Failed to generate final report summary: {e}", exc_info=True)
            return {}
 