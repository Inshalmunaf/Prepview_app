import cv2
import mediapipe as mp
import numpy as np
import math
import os
from pathlib import Path
from collections import deque, Counter
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import CVConfig

class CVAnalyzerComponent:
    def __init__(self, config: CVConfig):
        """
        Initializes the CV Analyzer component with Configuration ONLY.
        Video path is now passed during the 'run' method.
        """
        self.config = config
        
        # MediaPipe models initialization
        self.mp_face_mesh = mp.solutions.face_mesh
        
        # Initialize thresholds (will be set during calibration)
        self.THRESH_LIP_THICKNESS = 0.0
        self.THRESH_BROW_SQUEEZE = 0.0
        self.THRESH_BROW_DROP = 0.0
        
        # Static thresholds from config
        self.THRESH_HAPPY = self.config.expr_thresh_happy
        self.THRESH_SURPRISE = self.config.expr_thresh_surprise
        
        # Variable to hold current processing video path
        self.video_path = None
        
        logger.info("CVAnalyzerComponent Initialized.")

    # ==========================================================
    # 🧩 HELPER MODULES FOR EXPRESSION
    # ==========================================================
    
    def _expr_get_distance(self, p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    def _expr_get_face_scale(self, landmarks):
        left_eye = landmarks.landmark[33]
        right_eye = landmarks.landmark[263]
        width = self._expr_get_distance(left_eye, right_eye)
        return width if width > 0 else None

    def _expr_get_raw_metrics(self, landmarks, face_width):
        """Returns raw values for Lip, Squeeze, Drop."""
        # 1. Lip Thickness
        u_top, u_btm = landmarks.landmark[0], landmarks.landmark[13]
        l_top, l_btm = landmarks.landmark[14], landmarks.landmark[17]
        thick = (self._expr_get_distance(u_top, u_btm) + self._expr_get_distance(l_top, l_btm)) / face_width
        
        # 2. Brow Squeeze
        brow_l, brow_r = landmarks.landmark[107], landmarks.landmark[336]
        squeeze = self._expr_get_distance(brow_l, brow_r) / face_width
        
        # 3. Brow Drop
        l_drop = self._expr_get_distance(landmarks.landmark[159], landmarks.landmark[105]) / face_width
        r_drop = self._expr_get_distance(landmarks.landmark[386], landmarks.landmark[334]) / face_width
        drop = (l_drop + r_drop) / 2
        
        return thick, squeeze, drop

    def _expr_check_happy(self, landmarks, face_width):
        m_l = landmarks.landmark[61]
        m_r = landmarks.landmark[291]
        return (self._expr_get_distance(m_l, m_r) / face_width) > self.THRESH_HAPPY

    def _expr_check_surprise(self, landmarks, face_width):
        u_l = landmarks.landmark[13]
        l_l = landmarks.landmark[14]
        return (self._expr_get_distance(u_l, l_l) / face_width) > self.THRESH_SURPRISE

    def _expr_calibrate_user(self):
        """Phase 1: Calibrate Thresholds based on user's neutral face"""
        logger.info("🤖 Calibrating Baseline (Reading neutral face)...")
        cap = cv2.VideoCapture(self.video_path)
        
        lip_vals, sq_vals, drop_vals = [], [], []
        frames_read = 0
        limit_frames = self.config.expr_calibration_frames
        
        # Use separate face mesh context to ensure clean state
        with self.mp_face_mesh.FaceMesh(
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
            refine_landmarks=True
        ) as calibration_mesh:
            
            while cap.isOpened() and frames_read < limit_frames:
                ret, frame = cap.read()
                if not ret: break
                
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = calibration_mesh.process(rgb)
                
                if res.multi_face_landmarks:
                    landmarks = res.multi_face_landmarks[0]
                    face_width = self._expr_get_face_scale(landmarks)
                    
                    if face_width:
                        l, s, d = self._expr_get_raw_metrics(landmarks, face_width)
                        lip_vals.append(l)
                        sq_vals.append(s)
                        drop_vals.append(d)
                        frames_read += 1
        cap.release()

        # Set Dynamic Thresholds
        if lip_vals:
            base_lip = sum(lip_vals) / len(lip_vals)
            base_sq = sum(sq_vals) / len(sq_vals)
            base_drop = sum(drop_vals) / len(drop_vals)
            
            # Use Multipliers from Config
            self.THRESH_LIP_THICKNESS = base_lip * self.config.expr_sensitivity_lip
            self.THRESH_BROW_SQUEEZE = base_sq * self.config.expr_sensitivity_brow_squeeze
            self.THRESH_BROW_DROP = base_drop * self.config.expr_sensitivity_brow_drop
        else:
            logger.warning("❌ Failed to calibrate. Using defaults from config.")
            self.THRESH_LIP_THICKNESS = self.config.expr_default_lip_thickness
            self.THRESH_BROW_SQUEEZE = self.config.expr_default_brow_squeeze
            self.THRESH_BROW_DROP = self.config.expr_default_brow_drop

    def _expr_analyze_frame(self, landmarks):
        """Phase 2: Analyze single frame"""
        face_width = self._expr_get_face_scale(landmarks)
        if not face_width: return "neutral", []

        curr_lip, curr_sq, curr_drop = self._expr_get_raw_metrics(landmarks, face_width)

        # Check thresholds
        is_compressed = curr_lip < self.THRESH_LIP_THICKNESS
        is_brow_stress = (curr_sq < self.THRESH_BROW_SQUEEZE) or (curr_drop < self.THRESH_BROW_DROP)

        if self._expr_check_happy(landmarks, face_width): return "happy", []
        if self._expr_check_surprise(landmarks, face_width): return "surprise", []

        triggers = []
        if is_compressed: triggers.append("lip_compression")
        if is_brow_stress: triggers.append("brow_stress")

        if triggers: return "concerned", triggers
        return "neutral", []

    # ==========================================================
    # 3. MAIN EXPRESSION RUNNER
    # ==========================================================
    def _analyze_expressions(self):
        logger.info("Starting Expression & Nervousness Analysis...")
        
        # STEP 1: Run Calibration
        self._expr_calibrate_user()

        # STEP 2: Process Video
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or self.config.video_fps_fallback
        
        emotion_counts = {"neutral": 0, "happy": 0, "surprise": 0, "concerned": 0}
        nervousness_raw_counts = {"brow_stress": 0, "lip_compression": 0}
        analyzed_frames = 0
        frame_idx = 0
        frame_skip = self.config.expr_frame_skip

        with self.mp_face_mesh.FaceMesh(
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
            refine_landmarks=True
        ) as analysis_mesh:

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break

                if frame_idx % frame_skip == 0:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    res = analysis_mesh.process(rgb)

                    if res.multi_face_landmarks:
                        landmarks = res.multi_face_landmarks[0]
                        # Calling the modular function
                        emotion, triggers = self._expr_analyze_frame(landmarks)
                        
                        emotion_counts[emotion] += 1
                        analyzed_frames += 1
                        
                        for t in triggers:
                            if t in nervousness_raw_counts:
                                nervousness_raw_counts[t] += 1
                frame_idx += 1
        cap.release()

        # Stats Generation
        percentages = {k: round((v / analyzed_frames) * 100, 1) if analyzed_frames > 0 else 0 for k, v in emotion_counts.items()}
        nerv_pct = {k: round((v / analyzed_frames) * 100, 1) if analyzed_frames > 0 else 0 for k, v in nervousness_raw_counts.items()}
        dominant_mood = max(percentages, key=percentages.get) if percentages else "neutral"
        
        logger.info(f"Expression Analysis Done. Dominant: {dominant_mood}")

        return {
            "dominant_mood": dominant_mood,
            "emotion_distribution": percentages,
            "nervousness_analysis": {
                "total_concerned_percentage": percentages.get("concerned", 0),
                "breakdown": nerv_pct
            }
        }

    # ==========================================================
    # 1. HEAD MOVEMENT LOGIC
    # ==========================================================
    def _analyze_head_movement(self):
        logger.info("Starting Head Movement Analysis...")
        
        # Load from config
        threshold = self.config.head_movement_threshold
        facing_threshold = self.config.head_facing_threshold
        pitch_neutral_pct = self.config.head_pitch_neutral_pct
        smoothing_window = self.config.head_smoothing_window
        major_duration_threshold = self.config.head_major_event_duration
        time_gap_tolerance = self.config.head_time_gap_tolerance

        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        with self.mp_face_mesh.FaceMesh(
            min_detection_confidence=self.config.min_detection_confidence, 
            min_tracking_confidence=self.config.min_tracking_confidence
        ) as face_mesh:
            
            position_queue_x = deque(maxlen=smoothing_window)
            position_queue_y = deque(maxlen=smoothing_window)
            vertical_span_queue = deque(maxlen=30)
            all_detections = []
            prev_smoothed_x, prev_smoothed_y = None, None
            frame_count = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                frame_count += 1
                current_time = frame_count / fps
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)

                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        height, width, _ = frame.shape
                        nose_x = int(face_landmarks.landmark[1].x * width)
                        nose_y = int(face_landmarks.landmark[1].y * height)
                        left_ear_x = int(face_landmarks.landmark[234].x * width)
                        right_ear_x = int(face_landmarks.landmark[454].x * width)
                        forehead_y = int(face_landmarks.landmark[151].y * height)
                        chin_y = int(face_landmarks.landmark[175].y * height)

                        position_queue_x.append(nose_x)
                        position_queue_y.append(nose_y)
                        smoothed_x = sum(position_queue_x) / len(position_queue_x)
                        smoothed_y = sum(position_queue_y) / len(position_queue_y)
                        
                        current_span = chin_y - forehead_y
                        if current_span > 0: vertical_span_queue.append(current_span)
                        avg_span = sum(vertical_span_queue) / len(vertical_span_queue) if vertical_span_queue else current_span

                        current_state = "camera facing"
                        left_dist = smoothed_x - left_ear_x
                        right_dist = right_ear_x - smoothed_x
                        ear_diff = left_dist - right_dist
                        
                        is_looking_away_horizontal = abs(ear_diff) > facing_threshold
                        pitch_deviation = (current_span - avg_span) / avg_span if avg_span > 0 else 0
                        is_looking_away_vertical = abs(pitch_deviation) > pitch_neutral_pct

                        if is_looking_away_horizontal:
                            if ear_diff < 0: current_state = "left"
                            else: current_state = "right"
                        elif is_looking_away_vertical:
                            if pitch_deviation > 0: current_state = "up"
                            else: current_state = "down"
                        else:
                            if prev_smoothed_x is not None:
                                dx = smoothed_x - prev_smoothed_x
                                dy = smoothed_y - prev_smoothed_y
                                if abs(dx) > threshold or abs(dy) > threshold:
                                    pass 

                        all_detections.append({"timestamp": current_time, "type": current_state})
                        prev_smoothed_x, prev_smoothed_y = smoothed_x, smoothed_y
        cap.release()

        if not all_detections: return {"dominant_type": "None", "major_events": []}
        
        valid_moves = [d['type'] for d in all_detections if d['type'] != "camera facing"]
        dominant_type = Counter(valid_moves).most_common(1)[0][0] if valid_moves else "camera facing"
        
        major_events = []
        if len(all_detections) > 0:
            curr_start = all_detections[0]['timestamp']
            curr_type = all_detections[0]['type']
            for i in range(1, len(all_detections)):
                d = all_detections[i]
                if d['type'] != curr_type or (d['timestamp'] - all_detections[i-1]['timestamp'] > time_gap_tolerance):
                    if curr_type != "camera facing" and (all_detections[i-1]['timestamp'] - curr_start >= major_duration_threshold):
                        major_events.append(f"{curr_type} ({curr_start:.2f}s - {all_detections[i-1]['timestamp']:.2f}s)")
                    curr_start = d['timestamp']
                    curr_type = d['type']
            if curr_type != "camera facing" and (all_detections[-1]['timestamp'] - curr_start >= major_duration_threshold):
                major_events.append(f"{curr_type} ({curr_start:.2f}s - {all_detections[-1]['timestamp']:.2f}s)")

        return {"dominant_type": dominant_type, "major_events": major_events}

    # ==========================================================
    # 2. EYE GAZE LOGIC
    # ==========================================================
    def _analyze_eye_gaze(self):
        logger.info("Starting Eye Gaze Analysis...")
        
        # Load from config
        calibration_time = self.config.eye_calibration_time
        movement_threshold = self.config.eye_movement_threshold
        min_event_duration = self.config.eye_min_event_duration
        UP_SENSITIVITY = self.config.eye_up_sensitivity_multiplier

        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or self.config.video_fps_fallback

        LEFT_EYE = [33, 133]
        RIGHT_EYE = [362, 263]
        LEFT_IRIS = [468, 469, 470, 471]
        RIGHT_IRIS = [472, 473, 474, 475]

        dx_vals, dy_vals = [] , []
        frame_idx = 0
        def avg(lm, ids, w, h):
            return np.mean([(lm[i].x * w, lm[i].y * h) for i in ids], axis=0)

        with self.mp_face_mesh.FaceMesh(refine_landmarks=True) as face_mesh:
            # Pass 1: Calibration
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or (frame_idx/fps) > calibration_time: break
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = face_mesh.process(rgb)
                if res.multi_face_landmarks:
                    lm = res.multi_face_landmarks[0].landmark
                    eye = (avg(lm, LEFT_EYE, w, h) + avg(lm, RIGHT_EYE, w, h)) / 2
                    iris = (avg(lm, LEFT_IRIS, w, h) + avg(lm, RIGHT_IRIS, w, h)) / 2
                    dx_vals.append((iris[0] - eye[0]) / w)
                    dy_vals.append((iris[1] - eye[1]) / h)
                frame_idx += 1

            if not dx_vals: 
                cap.release()
                return {"eye_contact_percentage": 0, "major_movements": [], "timeline": []}
                
            base_dx, base_dy = np.mean(dx_vals), np.mean(dy_vals)

            # Pass 2: Analysis
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            events, current_state, state_start = [], None, 0
            total_time, total_center = 0, 0
            frame_idx = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = face_mesh.process(rgb)
                
                direction = "center"
                if res.multi_face_landmarks:
                    lm = res.multi_face_landmarks[0].landmark
                    eye = (avg(lm, LEFT_EYE, w, h) + avg(lm, RIGHT_EYE, w, h)) / 2
                    iris = (avg(lm, LEFT_IRIS, w, h) + avg(lm, RIGHT_IRIS, w, h)) / 2
                    dx = (iris[0] - eye[0]) / w - base_dx
                    dy = (iris[1] - eye[1]) / h - base_dy
                    
                    thresh_y = movement_threshold * UP_SENSITIVITY if dy < 0 else movement_threshold
                    if not (abs(dx) < movement_threshold and abs(dy) < thresh_y):
                        norm_dy = dy / UP_SENSITIVITY if dy < 0 else dy
                        if abs(dx) > abs(norm_dy): direction = "right" if dx > 0 else "left"
                        else: direction = "down" if dy > 0 else "up"
                
                t = frame_idx / fps
                if direction != current_state:
                    if current_state:
                        dur = t - state_start
                        total_time += dur
                        if current_state == "center": total_center += dur
                        if dur >= min_event_duration:
                            events.append({"timestamp": f"{state_start:.1f}s-{t:.1f}s", "direction": current_state})
                    current_state, state_start = direction, t
                frame_idx += 1
        cap.release()

        pct = round((total_center / total_time * 100), 2) if total_time > 0 else 0
        return {"eye_contact_percentage": pct, "major_movements": [e for e in events if e['direction']!='center'], "timeline": events}


    def nonverbal_score(self,expression, eye_gaze, head_movement):
        """
        Returns a non-verbal confidence score between 0 and 100
        """

        # ---------- 1. Facial Expression & Nervousness ----------
        neutral_pct = expression["emotion_distribution"].get("neutral", 0) / 100
        concerned_pct = expression["emotion_distribution"].get("concerned", 0) / 100
        lip_compression = (
            expression["nervousness_analysis"]["breakdown"].get("lip_compression", 0) / 100
        )

        facial_score = (
            0.6 * neutral_pct +
            0.4 * (1 - concerned_pct)
        )

        facial_score -= 0.3 * lip_compression
        facial_score = max(0.0, min(1.0, facial_score))


        # ---------- 2. Eye Gaze & Contact ----------
        eye_contact = eye_gaze.get("eye_contact_percentage", 0) / 100
        gaze_losses = sum(
            1 for t in eye_gaze.get("timeline", [])
            if t.get("eyecontact") == "lost"
        )

        if eye_contact < 0.6:
            eye_score = eye_contact
        elif eye_contact <= 0.85:
            eye_score = 1.0
        else:
            eye_score = 1 - (eye_contact - 0.85)

        eye_score -= min(0.15, gaze_losses * 0.05)
        eye_score = max(0.0, min(1.0, eye_score))


        # ---------- 3. Head Movement Stability ----------
        major_events = len(head_movement.get("major_events", []))

        if major_events == 0:
            head_score = 1.0
        elif major_events <= 2:
            head_score = 0.7
        else:
            head_score = 0.4


        # ---------- Final Weighted Score ----------
        final_score_0_1 = (
            0.40 * facial_score +
            0.45 * eye_score +
            0.15 * head_score
        )

        return round(final_score_0_1 * 100, 1)
    

    # ==========================================================
    # MAIN RUN (Aggregator)
    # ==========================================================
    def run(self, video_path_str: str) -> dict:
        """
        Runs the full CV analysis pipeline on the given video.
        
        Args:
            video_path_str (str): Path to the video file.
        """
        self.video_path = str(video_path_str) # Set path for this run
        
        if not os.path.exists(self.video_path):
            logger.error(f"Video file not found: {self.video_path}")
            return {}
            
        logger.info(f"--- Starting CV Analysis for: {Path(self.video_path).name} ---")
        
        head_data = self._analyze_head_movement()
        eye_data = self._analyze_eye_gaze()
        expr_data = self._analyze_expressions()
        cv_score = self.nonverbal_score(expr_data, eye_data, head_data)
        
        logger.info("--- Finished CV Analysis Component ---")
        return {
            "head_movement": head_data,
            "eye_gaze": eye_data,
            "facial_expression": expr_data,
            "cv_score" : cv_score
        }