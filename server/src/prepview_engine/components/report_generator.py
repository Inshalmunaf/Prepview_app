import requests
import json
import os
from dotenv import load_dotenv  # 👈 New Import
from typing import Dict
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import ReportGenerationConfig

# Load environment variables from .env file directly
load_dotenv()

class ReportGenerator:
    def __init__(self, config: ReportGenerationConfig):
        """
        Initializes the Report Generator using existing config for model params,
        but will fetch API Key directly from environment.
        """
        self.config = config
        logger.info(f" Report Generator Initialized (Provider: {self.config.provider}, Model: {self.config.model_name})")

    def generate_feedback(self, aggregated_data: Dict) -> str:
        """
        Generates feedback using Groq (via .env key) or Ollama.
        """
        if not aggregated_data:
            return "Error: No data provided for report generation."

        try:
            # 1. Extract Data
            # 1. Extract Aggregates Safely
            nlp = aggregated_data.get("nlp_aggregate", {})
            cv = aggregated_data.get("cv_aggregate", {})
            code = aggregated_data.get("code_aggregate", {}) # 🌟 Nayi Line

            # 2. Fill User Prompt
            user_prompt = self.config.user_prompt_template.format(
                # --- CV Metrics ---
                avg_cv_score=cv.get("avg_cv_score", 0),
                avg_eye_contact=cv.get("avg_eye_contact", 0),
                avg_nervousness=cv.get("avg_nervousness", 0),
                dominant_mood=cv.get("dominant_mood", "Neutral"),
                
                # --- NLP & Verbal Metrics ---
                avg_nlp_score=nlp.get("avg_nlp_score", 0),
                avg_wpm=nlp.get("avg_wpm", 0),
                avg_filler_rate=nlp.get("avg_filler_rate", 0),
                
                # 🌟 Nayi Linguistic Metrics 🌟
                avg_lexical_richness=nlp.get("avg_lexical_richness", 0),
                avg_repetition_ratio=nlp.get("avg_repetition_ratio", 0),
                avg_uncertainty=nlp.get("avg_uncertainty", 0),
                avg_semantic_instability=nlp.get("avg_semantic_instability", 0),
                
                # 🌟 Nayi Coding & Proctoring Metrics 🌟
                total_coding_questions_attempted=code.get("total_coding_questions_attempted", 0),
                avg_score_with_penalties=code.get("avg_score_with_penalties", 0),
                cheating_incidents=code.get("cheating_incidents", []),
                
                # --- Weakest Link Info ---
                weakest_answer_id=nlp.get("weakest_answer_id", "Unknown"),
                lowest_combined_score=nlp.get("lowest_combined_score", 0),
                transcript_sample=nlp.get("transcript_sample", "No text available.")
            )

            logger.info(f"⏳ Sending request to {self.config.provider.upper()}...")

            # ==========================================
            # OPTION A: GROQ API LOGIC (Direct .env Access)
            # ==========================================
            if self.config.provider == "groq":
                # 👇 DIRECTLY FETCH KEY FROM ENV
                api_key = os.getenv("GROQ_API_KEY")

                if not api_key:
                    logger.error("❌ GROQ_API_KEY not found in .env file!")
                    return "Error: API Key missing in environment."

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.config.model_name, # YAML se model name
                    "messages": [
                        {"role": "system", "content": self.config.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                }

                # YAML se base_url uthayen (ensure karein wo groq ka URL ho)
                # Agar YAML mein localhost hai, to yahan hardcode kar dein:
                # url = "https://api.groq.com/openai/v1/chat/completions"
                url = self.config.base_url 

                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    result_text = data["choices"][0]["message"]["content"]
                    logger.info("✅ Report Generated via Groq!")
                    return result_text
                else:
                    error_msg = f"Groq API Error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return f"Error: {error_msg}"

            # ==========================================
            # OPTION B: OLLAMA API LOGIC
            # ==========================================
            else:
                full_prompt = f"{self.config.system_prompt}\n\n{user_prompt}"
                payload = {
                    "model": self.config.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                }
                
                response = requests.post(self.config.base_url, json=payload, timeout=300)
                
                if response.status_code == 200:
                    result_text = response.json().get("response", "")
                    logger.info("✅ Report Generated via Ollama!")
                    return result_text
                else:
                    logger.error(f"Ollama Error: {response.status_code}")
                    return "Error: Could not generate report locally."

        except Exception as e:
            logger.error(f"Report Generation Critical Failure: {e}")
            return f"An error occurred: {e}"