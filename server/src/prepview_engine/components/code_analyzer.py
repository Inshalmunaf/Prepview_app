import requests
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any

from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import CodeAnalysisConfig

from prepview_engine.utils.common import logger

import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp

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
            self.weights = self.config.weights
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
            Return a raw JSON object with ONLY a "scores" object. Do NOT include any feedback strings.
            Example:
            {{
                "scores": {{
                    "correctness": 8,
                    "code_quality": 7,
                    "problem_solving": 9,
                    "efficiency": 8,
                    "best_practices": 7
                }}
            }}
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

            # 🌟 UPDATE: Removed overall_feedback, returning ONLY what you requested
            return {
                "success": True,
                "final_score": final_score,
                "category_scores": raw_scores
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {result_text}")
            return {
                "success": False,
                "final_score": 0,
                "error_message": "AI returned invalid format.",
                
            }
        except Exception as e:
            logger.error(f"Code Evaluation Critical Failure: {e}")
            return {
                "success": False,
                "final_score": 0,
                "error_message": "An error occurred during evaluation.",
                
            }



# ==========================================
# HELPER FUNCTION: FACE & GAZE ANALYSIS
# ==========================================
    def analyze_gaze_and_face(self, frame, face_mesh_model, img_w, img_h):
        """
        Analyzes a single frame using MediaPipe Face Mesh.
        Returns: (persons_in_frame: int, is_looking_away: bool)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mesh_results = face_mesh_model.process(rgb_frame)
        
        persons_in_frame = 0
        is_looking_away = False

        if not mesh_results.multi_face_landmarks:
            return persons_in_frame, is_looking_away
            
        persons_in_frame = len(mesh_results.multi_face_landmarks)
        
        # Gaze Tracking (Check primary face)
        primary_face = mesh_results.multi_face_landmarks[0]
        
        # CORRECTED 3D FACE POINTS FOR OPENCV (Y is positive downwards)
        face_3d = np.array([
            [0.0, 0.0, 0.0],            # Nose tip
            [0.0, 330.0, -65.0],        # Chin 
            [-225.0, -170.0, -135.0],   # Left eye corner 
            [225.0, -170.0, -135.0],    # Right eye corner
            [-150.0, 150.0, -125.0],    # Left mouth corner
            [150.0, 150.0, -125.0]      # Right mouth corner
        ], dtype=np.float64)
        
        # Extract 2D Frame Points
        face_2d = []
        for idx in [1, 152, 33, 263, 61, 291]:
            lm = primary_face.landmark[idx]
            x, y = int(lm.x * img_w), int(lm.y * img_h)
            face_2d.append([x, y])
            
        face_2d = np.array(face_2d, dtype=np.float64)

        # Camera Math setup
        focal_length = 1 * img_w
        cam_matrix = np.array([
            [focal_length, 0, img_h / 2],
            [0, focal_length, img_w / 2],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_matrix = np.zeros((4, 1), dtype=np.float64)

        # Calculate Head Rotation
        success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)
        if success:
            rmat, _ = cv2.Rodrigues(rot_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

            # OpenCV returns degrees directly
            pitch = angles[0]
            yaw = angles[1]

            # GAZE THRESHOLDS
            # Yaw: -25 to 25 (Left/Right limits)
            # Pitch: -25 to 35 (Up/Down limits - allowing natural laptop gaze)
            if yaw < -25 or yaw > 25 or pitch < -25 or pitch > 35:
                is_looking_away = True
                
        return persons_in_frame, is_looking_away


# ==========================================
# MAIN FUNCTION: VIDEO PIPELINE
# ==========================================
    def analyze_video_for_cheating_master(self,video_path: str) -> Dict[str, Any]:
        """
        Main entry point for proctoring analysis.
        Uses YOLOv8 for object detection and MediaPipe for face/gaze analysis.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return {"success": False, "error": "Video not found"}

        logger.info(f"--- Starting Master Proctoring Analysis for: {os.path.basename(video_path)} ---")
        
        # 1. Initialize Models
        try:
            yolo_model = YOLO('yolov8s.pt') 
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return {"success": False, "error": str(e)}

        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5, max_num_faces=5)

        # 2. Setup Video Properties
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps == 0: fps = 30 
        
        img_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        img_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Tracking Metrics
        total_frames_processed = 0
        phone_detected_frames = 0
        book_or_laptop_detected_frames = 0
        multiple_persons_frames = 0
        no_person_frames = 0
        looking_away_frames = 0

        frame_skip = max(1, fps // 2) 
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % frame_skip != 0:
                continue 
                
            total_frames_processed += 1

            # --- A. Face & Gaze Detection ---
            persons_in_frame, is_looking_away = self.analyze_gaze_and_face(frame, face_mesh, img_w, img_h)

            if persons_in_frame == 0:
                no_person_frames += 1
            elif persons_in_frame > 1:
                multiple_persons_frames += 1
                
            if is_looking_away:
                looking_away_frames += 1

            # --- B. Object Detection ---
            # TWEAK: Lowered confidence to 0.25 to catch dark phones on dark clothing better
            yolo_results = yolo_model(frame, conf=0.25, verbose=False)
            for r in yolo_results:
                boxes = r.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    if cls_id == 67: # Phone
                        phone_detected_frames += 1
                    elif cls_id in [73, 63]: # Book / Laptop
                        book_or_laptop_detected_frames += 1

        cap.release()
        face_mesh.close()

        # ==========================================
        # MATH: CONVERT FRAMES TO SECONDS & PCT
        # ==========================================
        seconds_per_processed_frame = frame_skip / fps 
        
        # Calculate Seconds
        total_seconds_analyzed = round(total_frames_processed * seconds_per_processed_frame, 1)
        phone_seconds = round(phone_detected_frames * seconds_per_processed_frame, 1)
        book_seconds = round(book_or_laptop_detected_frames * seconds_per_processed_frame, 1)
        multiple_people_seconds = round(multiple_persons_frames * seconds_per_processed_frame, 1)
        away_from_camera_seconds = round(no_person_frames * seconds_per_processed_frame, 1)
        gaze_away_seconds = round(looking_away_frames * seconds_per_processed_frame, 1)

        # Calculate Percentages (Used exclusively for IF conditions)
        multiple_people_pct = (multiple_persons_frames / total_frames_processed) * 100 if total_frames_processed > 0 else 0
        away_pct = (no_person_frames / total_frames_processed) * 100 if total_frames_processed > 0 else 0
        gaze_away_pct = (looking_away_frames / total_frames_processed) * 100 if total_frames_processed > 0 else 0

        # ==========================================
        # FINAL VERDICT
        # ==========================================
        is_cheating = False
        reasons = []

        # Object Thresholds
        if phone_detected_frames >= 3:
            is_cheating = True
            reasons.append(f"Cell phone detected (visible for ~{phone_seconds} seconds).")
            
        if book_or_laptop_detected_frames >= 3:
            is_cheating = True
            reasons.append(f"Book/Notes/Screen detected (visible for ~{book_seconds} seconds).")
            
        # Face & Gaze Thresholds (Comparing percentages, printing seconds)
        if total_frames_processed > 0:
            if multiple_people_pct > 2.0:
                is_cheating = True
                reasons.append(f"Multiple people detected in frame (for ~{multiple_people_seconds} seconds).")
                
            if away_pct > 10.0: 
                is_cheating = True
                reasons.append(f"Candidate left the camera view (for ~{away_from_camera_seconds} seconds).")
                
            if gaze_away_pct > 15.0:
                is_cheating = True
                reasons.append(f"Candidate frequently looked away from the screen (for ~{gaze_away_seconds} seconds).")

        logger.info(f"--- Finished. Cheating Suspected: {is_cheating} ---")
        
        return {
            "success": True,
            "is_cheating_suspected": is_cheating,
            "reasons": reasons,
            "stats": {
                "total_video_duration_analyzed_seconds": total_seconds_analyzed,
                "phone_detected_seconds": phone_seconds,
                "book_or_laptop_detected_seconds": book_seconds,
                "multiple_people_seconds": multiple_people_seconds,
                "away_from_camera_seconds": away_from_camera_seconds,
                "gaze_away_seconds": gaze_away_seconds,
                "multiple_people_pct": round(multiple_people_pct, 2),
                "away_from_camera_pct": round(away_pct, 2),
                "gaze_away_pct": round(gaze_away_pct, 2)
            }
        }

    def generate_final_interview_score(self, question: str, code: str, language: str, video_path: str) -> Dict[str, Any]:
        """
        Takes inputs for both code evaluation and proctoring.
        Calculates a final penalized score based on cheating severity.
        """
        logger.info("Generating Final Interview Score...")

        # ==========================================
        # STEP 1: CODE EVALUATION
        # ==========================================
        # Calling your evaluate_code function
        eval_result = self.evaluate_code(question, code, language)
        tech_score = eval_result.get("final_score", 0)

        # ==========================================
        # STEP 2: VIDEO PROCTORING
        # ==========================================
        # Calling the master cheating analyzer
        proctoring_result = self.analyze_video_for_cheating_master(video_path)
        is_cheating = proctoring_result.get("is_cheating_suspected", False)
        reasons = proctoring_result.get("reasons", [])
        print(reasons)
        # ==========================================
        # STEP 3: CALCULATE PENALTIES
        # ==========================================
        total_penalty = 0
        
        if is_cheating:
            for reason in reasons:
                # Severe Violations (Instant Fail)
                if "Cell phone detected" in reason:
                    total_penalty += 100
                elif "Book/Notes/Screen" in reason:
                    total_penalty += 100
                # Major Violations
                elif "Multiple people" in reason:
                    total_penalty += 40
                # Minor/Medium Violations
                elif "left the camera" in reason:
                    total_penalty += 20
                elif "looked away" in reason:
                    total_penalty += 15

        # Ensure score doesn't go below 0
        score_with_penalties = max(0, tech_score - total_penalty)

        # ==========================================
        # STEP 4: RETURN UNIFIED JSON
        # ==========================================
        return {
            "success": eval_result.get("success", False) and proctoring_result.get("success", False),
            "original_technical_score": tech_score,
            "score_with_penalties": score_with_penalties,
            "proctoring_results": {
                "is_cheating_suspected": is_cheating,
                "reasons": reasons,
                "stats": proctoring_result.get("stats", {})
            }
        }
        
    def run(self, question: str, code: str, language: str, video_path_str: str) -> Dict[str, Any]:
        """
        Runs the full Interview Analysis pipeline (Code Evaluation + AI Proctoring).
        This acts as the standard entry point for the AnalysisPipeline.
        
        Args:
            question (str): The full context/description of the interview question.
            code (str): The candidate's submitted code.
            language (str): The programming language used (e.g., 'python', 'javascript').
            video_path_str (str): Path to the candidate's recorded interview video.
            
        Returns:
            Dict[str, Any]: The structured evaluation and proctoring results.
        """
        import os # Make sure this is imported at the top of your file
        
        logger.info(f"--- Starting Full Interview Analysis for {language.upper()} submission ---")
        
        # 1. Basic validation: Check if code exists
        if not code or not code.strip():
            logger.warning("Empty code submission received. Aborting analysis.")
            return {
                "success": False,
                "original_technical_score": 0,
                "score_with_penalties": 0,
                "error_message": "No code was provided to analyze."
            }
            
        # 2. Basic validation: Check if video file exists
        if not video_path_str or not os.path.exists(video_path_str):
            logger.error(f"Proctoring video not found at: {video_path_str}. Aborting analysis.")
            return {
                "success": False,
                "original_technical_score": 0,
                "score_with_penalties": 0,
                "error_message": "Proctoring video is missing or invalid. Cannot verify candidate integrity."
            }
            
        # 3. Execute the core unified scoring logic
        logger.info("Code and video validated. Passing to Unified Scoring Engine...")
        final_results = self.generate_final_interview_score(
            question=question, 
            code=code, 
            language=language, 
            video_path=video_path_str
        )
        
        # 4. Log the outcomes clearly
        if final_results.get("success"):
            tech_score = final_results.get("original_technical_score")
            final_score = final_results.get("score_with_penalties")
            logger.info(f"Analysis Complete! Tech Score: {tech_score}/100 | Final Penalized Score: {final_score}/100")
            
            # Check if cheating was caught and log a warning
            if final_results.get("proctoring_results", {}).get("is_cheating_suspected"):
                logger.warning("⚠️ Proctoring flags raised! Cheating suspected during the interview.")
        else:
            logger.error("Interview Analysis failed during execution.")
            
        logger.info("--- Finished Full Interview Analysis Component ---")
        
        return final_results