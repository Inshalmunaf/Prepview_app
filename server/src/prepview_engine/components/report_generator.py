import requests
import json
from typing import Dict
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import ReportGenerationConfig

class ReportGenerator:
    def __init__(self, config: ReportGenerationConfig):
        """
        Initializes the Report Generator with LLM settings.
        """
        self.config = config
        logger.info(f"🤖 Report Generator Initialized (Model: {self.config.model_name})")

    def generate_feedback(self, aggregated_data: Dict) -> str:
        """
        Takes the dictionary from ResultAggregator, fills the prompt, 
        and gets a response from Ollama.
        """
        if not aggregated_data:
            return "Error: No data provided for report generation."

        try:
            # 1. Extract Data from Aggregator Output
            nlp = aggregated_data.get("nlp_aggregate", {})
            cv = aggregated_data.get("cv_aggregate", {})

            # 2. Fill the Prompt Template (Dynamic Data Injection)
            user_prompt = self.config.user_prompt_template.format(
                # CV Metrics
                avg_cv_score=cv.get("avg_cv_score", 0),
                avg_eye_contact=cv.get("avg_eye_contact", 0),
                avg_nervousness=cv.get("avg_nervousness", 0),
                dominant_mood=cv.get("dominant_mood", "Neutral"),
                
                # NLP Metrics
                avg_nlp_score=nlp.get("avg_nlp_score", 0),
                avg_wpm=nlp.get("avg_wpm", 0),
                avg_filler_rate=nlp.get("avg_filler_rate", 0),
                
                # Weakest Link Context
                weakest_answer_id=nlp.get("weakest_answer_id", "Unknown"),
                lowest_combined_score=nlp.get("lowest_combined_score", 0),
                transcript_sample=nlp.get("transcript_sample", "No text available.")
            )

            # 3. Combine System + User Prompt
            full_prompt = f"{self.config.system_prompt}\n\n{user_prompt}"
            
            logger.info("⏳ Sending data to LLM for analysis...")

            # 4. Prepare Payload for Ollama
            payload = {
                "model": self.config.model_name,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                }
            }

            # 5. Call API
            response = requests.post(self.config.base_url, json=payload, timeout=300)
            
            if response.status_code == 200:
                result_text = response.json().get("response", "")
                logger.info(" Feedback Report Generated Successfully!")
                return result_text
            else:
                error_msg = f"LLM API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return "Could not generate feedback due to AI server error."

        except Exception as e:
            logger.error(f"Report Generation Failed: {e}")
            return f"An error occurred while generating the report: {e}"