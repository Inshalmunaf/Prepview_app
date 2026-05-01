import requests
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any

from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import CodeAnalysisConfig

from prepview_engine.utils.common import logger

load_dotenv()

class CodeAnalyzer:
    def __init__(self, config: CodeAnalysisConfig):
        """
        Initializes the Code Analyzer by automatically fetching 
        configurations and grading weights via the central ConfigurationManager.
        """
        try:
            # 1. Initialize central config manager (jo params.yaml read karega)
            self.config = config
            
            logger.info(f"🚀 Code Analyzer Initialized (Provider: {self.config.provider}, Model: {self.config.model_name})")
            logger.debug(f"⚖️ Using Grading Weights: {self.weights}")
            
        except Exception as e:
            logger.error(f" Failed to initialize CodeAnalyzer: {e}")
            raise e

    # ... (Aapka evaluate_code function yahan neechay waisay hi rahega) ...

    def evaluate_code(self, question: str, code: str, language: str) -> Dict[str, Any]:
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
            You are an expert Technical Interviewer evaluating a candidate's code submission.
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
            # OPTION A: GROQ API LOGIC
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
                    "temperature": self.config.temperature,  # Fetching dynamically from config
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
                        "temperature": self.config.temperature,
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

            # Calculate Final Weighted Score (Out of 100) using safe .get()
            final_score = 0.0
            
            final_score += float(raw_scores.get("correctness", 0)) * self.weights.get("correctness", 0.30) * 10
            final_score += float(raw_scores.get("code_quality", 0)) * self.weights.get("code_quality", 0.25) * 10
            final_score += float(raw_scores.get("problem_solving", 0)) * self.weights.get("problem_solving", 0.20) * 10
            final_score += float(raw_scores.get("efficiency", 0)) * self.weights.get("efficiency", 0.15) * 10
            final_score += float(raw_scores.get("best_practices", 0)) * self.weights.get("best_practices", 0.10) * 10

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
        
    def run(self, question: str, code: str, language: str, video_path_str: str) -> Dict[str, Any]:
        """
        Runs the full Code Analysis pipeline for a given candidate's code submission.
        This acts as the standard entry point for the AnalysisPipeline.
        
        Args:
            question (str): The full context/description of the interview question.
            code (str): The candidate's submitted code.
            language (str): The programming language used (e.g., 'python', 'javascript').
            field (str): The target job field (default: 'Software Engineering').
            
        Returns:
            Dict[str, Any]: The structured evaluation results.
        """
        logger.info(f"--- Starting Code Analysis for {language.upper()} submission ---")
        
        # Basic validation before hitting the heavy API
        if not code or not code.strip():
            logger.warning("Empty code submission received. Aborting analysis.")
            return {
                "success": False,
                "final_score": 0,
                "error_message": "No code was provided to analyze."
            }
            
        # Execute the core evaluation logic
        evaluation_results = self.evaluate_code(
            question=question, 
            code=code, 
            language=language, 
        )
        
        # Log success or failure based on the result
        if evaluation_results.get("success"):
            logger.info(f"Score Generated: {evaluation_results.get('final_score')}/100")
        else:
            logger.error("Code Analysis failed during evaluation.")
            
        logger.info("--- Finished Code Analysis Component ---")
        
        return evaluation_results