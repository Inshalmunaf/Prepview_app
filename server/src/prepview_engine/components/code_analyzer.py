import requests
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any
from prepview_engine.utils.common import logger

# Note: Aapko config files mein 'CodeAnalysisConfig' define karni hogi
from prepview_engine.config.configuration import CodeAnalysisConfig

# Load environment variables from .env file directly
load_dotenv()

class CodeAnalyzer:
    def __init__(self, config: CodeAnalysisConfig):
        """
        Initializes the Code Analyzer using existing config for model params.
        Fetches API Key directly from environment.
        """
        self.config = config
        
        # Define exact weights for evaluation
        self.weights = {
            "correctness": 0.30,
            "code_quality": 0.25,
            "problem_solving": 0.20,
            "efficiency": 0.15,
            "best_practices": 0.10,
        }
        logger.info(f"🚀 Code Analyzer Initialized (Provider: {self.config.provider}, Model: {self.config.model_name})")

    def evaluate_code(self, question: str, code: str, language: str, field: str) -> Dict[str, Any]:
        """
        Evaluates candidate's code using Groq or Ollama, calculates a 100-point score,
        and returns a structured dictionary.
        """
        if not code or not question:
            return {
                "success": False, 
                "final_score": 0, 
                "error_message": "Missing question or code for evaluation."
            }

        try:
            # 1. Prepare Prompts
            system_prompt = f"""
            You are an expert {field} Technical Interviewer evaluating a candidate's code submission.
            Evaluate the candidate's solution strictly on 5 dimensions. Assign a raw score from 0 to 10 for each category (where 0 is terrible and 10 is perfect).

            STRICT RULES (CRITICAL):
            1. correctness (0-10): Does the code logically solve the core problem?
            2. code_quality (0-10): Is the code clean, readable, modular, and well-structured?
            3. problem_solving (0-10): Is the algorithm and approach sound?
            4. efficiency (0-10): Is the time/space complexity optimal?
            5. best_practices (0-10): Are edge cases, errors, and null values handled properly?

            REQUIRED JSON OUTPUT FORMAT:
            Return a raw JSON object with a "scores" object and a "feedback" string.
            """

            user_prompt = f"""
            INTERVIEW QUESTION:
            {question}

            CANDIDATE'S SUBMITTED CODE ({language}):
            {code}
            """

            logger.info(f"⏳ Sending code evaluation request to {self.config.provider.upper()}...")
            result_text = ""

            # ==========================================
            # OPTION A: GROQ API LOGIC (Direct .env Access)
            # ==========================================
            if self.config.provider == "groq":
                api_key = os.getenv("GROQ_API_KEY")

                if not api_key:
                    logger.error("GROQ_API_KEY not found in .env file!")
                    raise ValueError("API Key missing in environment.")

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.config.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,  # Hardcoded low temperature for strict evaluation
                    "max_tokens": self.config.max_tokens,
                    "response_format": {"type": "json_object"} # ✨ CRITICAL for JSON output
                }

                url = self.config.base_url 

                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    result_text = data["choices"][0]["message"]["content"]
                    logger.info("✅ Code Evaluation Generated via Groq!")
                else:
                    error_msg = f"Groq API Error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

            # ==========================================
            # OPTION B: OLLAMA API LOGIC
            # ==========================================
            else:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                payload = {
                    "model": self.config.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "format": "json", # ✨ Forces Ollama to return JSON
                    "options": {
                        "temperature": 0.2,
                        "num_predict": self.config.max_tokens
                    }
                }
                
                response = requests.post(self.config.base_url, json=payload, timeout=300)
                
                if response.status_code == 200:
                    result_text = response.json().get("response", "")
                    logger.info("✅ Code Evaluation Generated via Ollama!")
                else:
                    logger.error(f"Ollama Error: {response.status_code}")
                    raise Exception("Could not evaluate code locally.")

            # ==========================================
            # JSON PARSING & SCORE CALCULATION
            # ==========================================
            
            # Clean up potential markdown formatting from LLM
            clean_json_str = result_text.replace("```json", "").replace("```", "").strip()
            llm_response = json.loads(clean_json_str)
            raw_scores = llm_response.get("scores", {})

            # Calculate Final Weighted Score (Out of 100)
            final_score = 0.0
            final_score += float(raw_scores.get("correctness", 0)) * self.weights["correctness"] * 10
            final_score += float(raw_scores.get("code_quality", 0)) * self.weights["code_quality"] * 10
            final_score += float(raw_scores.get("problem_solving", 0)) * self.weights["problem_solving"] * 10
            final_score += float(raw_scores.get("efficiency", 0)) * self.weights["efficiency"] * 10
            final_score += float(raw_scores.get("best_practices", 0)) * self.weights["best_practices"] * 10

            final_score = round(final_score)

            return {
                "success": True,
                "final_score": final_score,
                "category_scores": raw_scores,
                "overall_feedback": llm_response.get("feedback", "Good attempt.")
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {result_text}")
            return {
                "success": False,
                "final_score": 0,
                "error_message": "AI returned invalid format.",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"Code Evaluation Critical Failure: {e}")
            return {
                "success": False,
                "final_score": 0,
                "error_message": "An error occurred during evaluation.",
                "details": str(e)
            }