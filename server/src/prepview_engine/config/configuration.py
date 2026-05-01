from prepview_engine.utils.common import read_yaml, logger
from prepview_engine.constants import CONFIG_FILE_PATH, PARAMS_FILE_PATH
from pydantic import BaseModel, DirectoryPath, FilePath
from pathlib import Path
import os
from dotenv import load_dotenv
# --- Step 1: Define data structures using Pydantic ---
# Ye models hamain config.yaml ki structure ko validate karnay mai madad dengay
# Aur IDE par auto-completion bhi dengey.
load_dotenv()
class DatabaseConfig(BaseModel):
    connection_url: str

    def get_sqlalchemy_uri(self) -> str:
        """Returns the formatted connection string"""
        return self.connection_url

class PreprocessingConfig(BaseModel):
    # DirectoryPath check karay ga kay ye folder exist karta hai
    temp_video_path: Path 

class NLPConfig(BaseModel):
    # Models
    whisper_model: str
    whisper_language: str
    spacy_model: str
    transformer_model: str
    
    # Processing
    pause_threshold: float
    
    # Scoring - Speech Fluency
    wpm_min: int
    wpm_max: int
    wpm_strict_min: int
    wpm_strict_max: int
    penalty_wpm_high: int
    penalty_wpm_med: int
    
    rhythm_stability_high: float
    rhythm_stability_med: float
    penalty_rhythm_high: int
    penalty_rhythm_med: int
    
    # Scoring - Pause & Hesitation
    pause_ratio_high: float
    pause_ratio_med: float
    penalty_pause_ratio_high: int
    penalty_pause_ratio_med: int
    
    avg_pause_high: float
    avg_pause_med: float
    penalty_avg_pause_high: int
    penalty_avg_pause_med: int
    
    filler_rate_high: float
    filler_rate_med: float
    penalty_filler_high: int
    penalty_filler_med: int
    
    # Scoring - Linguistic Clarity
    lexical_richness_low: float
    lexical_richness_med: float
    penalty_lexical_high: int
    penalty_lexical_med: int
    
    repetition_ratio_high: float
    repetition_ratio_med: float
    penalty_repetition_high: int
    penalty_repetition_med: int
    
    # Scoring - Structural Stability
    sentence_length_std_high: int
    sentence_length_std_med: int
    penalty_sent_std_high: int
    penalty_sent_std_med: int
    
    aux_verb_ratio_high: float
    penalty_aux_verb: int
    
    semantic_instability_high: float
    semantic_instability_med: float
    penalty_semantic_high: int
    penalty_semantic_med: int

    # Scoring - Prosodic Confidence 
    prosodic_confidence_low: float
    prosodic_confidence_med: float
    penalty_prosodic_high: int
    penalty_prosodic_med: int

class ScoringConfig(BaseModel):
    gaze_good_threshold: int
    gaze_avg_threshold: int
    filler_good_threshold: int
    filler_avg_threshold: int

class ConfidenceTrainingConfig(BaseModel):
    root_dir: Path
    dataset_path: Path
    model_save_path: Path
    scaler_save_path: Path
    n_estimators: int
    random_state: int
    test_size: float

class CVConfig(BaseModel):
    # General MediaPipe settings
    min_detection_confidence: float
    min_tracking_confidence: float
    video_fps_fallback: float

    # Head Movement Params
    head_movement_threshold: int
    head_facing_threshold: int
    head_pitch_neutral_pct: float
    head_smoothing_window: int
    head_major_event_duration: float
    head_time_gap_tolerance: float

    # Eye Gaze Params
    eye_calibration_time: float
    eye_movement_threshold: float
    eye_min_event_duration: float
    eye_up_sensitivity_multiplier: float

    # Expression Params
    expr_calibration_frames: int
    expr_frame_skip: int
    
    # Universal Emotion Thresholds
    expr_thresh_happy: float
    expr_thresh_surprise: float
    
    # Nervousness Sensitivity (Multipliers)
    expr_sensitivity_lip: float
    expr_sensitivity_brow_squeeze: float
    expr_sensitivity_brow_drop: float
    
    # Fallback Defaults (Used if calibration fails)
    expr_default_lip_thickness: float
    expr_default_brow_squeeze: float
    expr_default_brow_drop: float
    
class CodeAnalysisConfig(BaseModel):
    provider: str
    model_name: str
    base_url: str
    max_tokens: int
    temperature: float
    weights: Dict[str, float]

class ReportGenerationConfig(BaseModel):
    provider: str
    model_name: str
    base_url: str
    temperature: float
    max_tokens: int
    system_prompt: str
    user_prompt_template: str


# --- Step 2: The Main Configuration Manager Class ---

class ConfigurationManager:
    def __init__(
        self,
        config_filepath=CONFIG_FILE_PATH,
        params_filepath=PARAMS_FILE_PATH):
        
        try:
            self.config = read_yaml(config_filepath)
            self.params = read_yaml(params_filepath)
            
            # config.yaml say artifacts_root ko create karna
            # (ye .gitignore mai hona chahaiye)
            os.makedirs(self.config.artifacts_root, exist_ok=True)
            
            logger.info("Configuration files loaded and artifacts root directory ensured.")
            
        except Exception as e:
            logger.error(f"Error loading configuration files: {e}")
            raise

    # --- Step 3: Getter methods ---
    # Har component/pipeline apni config in methods say mangay ga.
    
    def get_database_config(self) -> DatabaseConfig:
        """
        Returns database configuration.
        - Fetches the full DATABASE_URL from .env
        """
        try:
            # 1. Fetch URL from .env
            db_url = os.getenv("DATABASE_URL")

            # 2. Validation
            if not db_url:
                raise ValueError(" Error: DATABASE_URL is missing in .env file!")

            # 3. SQLAlchemy Driver Fix (Optional but Recommended)
            # Neon deta hai: postgresql://...
            # SQLAlchemy chahta hai: postgresql+psycopg2://...
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

            # 4. Return Config Object
            return DatabaseConfig(
                connection_url=db_url
            )
            
        except Exception as e:
            # logger.error(f"Error parsing database config: {e}") # Agar logger defined hai to uncomment karein
            print(f" Error parsing database config: {e}")
            raise e

    def get_preprocessing_config(self) -> PreprocessingConfig:
        """Returns preprocessing configuration (e.g., file paths)"""
        try:
            # config.yaml say artifacts_root aur temp_video_path ko join karna
            temp_path = Path(os.path.join(
                self.config.artifacts_root, 
                self.config.temp_video_path
            ))
            # Ensure directory exists
            os.makedirs(temp_path, exist_ok=True) 

            return PreprocessingConfig(temp_video_path=temp_path)
            
        except Exception as e:
            logger.error(f"Error parsing preprocessing config: {e}")
            raise

    def get_nlp_config(self) -> NLPConfig:
        """Returns NLP analysis parameters from params.yaml"""
        try:
            nlp = self.params.nlp_analysis
            models = nlp.models
            proc = nlp.processing
            sc = nlp.scoring
            
            return NLPConfig(
                # Models
                whisper_model=models.whisper_model,
                whisper_language=models.whisper_language,
                spacy_model=models.spacy_model,
                transformer_model=models.transformer_model,
                
                # Processing
                pause_threshold=proc.pause_threshold,
                
                # Scoring - Fluency
                wpm_min=sc.wpm_min, wpm_max=sc.wpm_max,
                wpm_strict_min=sc.wpm_strict_min, wpm_strict_max=sc.wpm_strict_max,
                penalty_wpm_high=sc.penalty_wpm_high, penalty_wpm_med=sc.penalty_wpm_med,
                
                rhythm_stability_high=sc.rhythm_stability_high, rhythm_stability_med=sc.rhythm_stability_med,
                penalty_rhythm_high=sc.penalty_rhythm_high, penalty_rhythm_med=sc.penalty_rhythm_med,
                
                # Scoring - Pause
                pause_ratio_high=sc.pause_ratio_high, pause_ratio_med=sc.pause_ratio_med,
                penalty_pause_ratio_high=sc.penalty_pause_ratio_high, penalty_pause_ratio_med=sc.penalty_pause_ratio_med,
                
                avg_pause_high=sc.avg_pause_high, avg_pause_med=sc.avg_pause_med,
                penalty_avg_pause_high=sc.penalty_avg_pause_high, penalty_avg_pause_med=sc.penalty_avg_pause_med,
                
                filler_rate_high=sc.filler_rate_high, filler_rate_med=sc.filler_rate_med,
                penalty_filler_high=sc.penalty_filler_high, penalty_filler_med=sc.penalty_filler_med,
                
                # Scoring - Linguistic
                lexical_richness_low=sc.lexical_richness_low, lexical_richness_med=sc.lexical_richness_med,
                penalty_lexical_high=sc.penalty_lexical_high, penalty_lexical_med=sc.penalty_lexical_med,
                
                repetition_ratio_high=sc.repetition_ratio_high, repetition_ratio_med=sc.repetition_ratio_med,
                penalty_repetition_high=sc.penalty_repetition_high, penalty_repetition_med=sc.penalty_repetition_med,
                
                # Scoring - Structural
                sentence_length_std_high=sc.sentence_length_std_high, sentence_length_std_med=sc.sentence_length_std_med,
                penalty_sent_std_high=sc.penalty_sent_std_high, penalty_sent_std_med=sc.penalty_sent_std_med,
                
                aux_verb_ratio_high=sc.aux_verb_ratio_high, penalty_aux_verb=sc.penalty_aux_verb,
                
                semantic_instability_high=sc.semantic_instability_high, semantic_instability_med=sc.semantic_instability_med,
                penalty_semantic_high=sc.penalty_semantic_high, penalty_semantic_med=sc.penalty_semantic_med,

                # Scoring - Prosodic 
                prosodic_confidence_low = sc.prosodic_confidence_low,
                prosodic_confidence_med = sc.prosodic_confidence_med,
                penalty_prosodic_high = sc.penalty_prosodic_high,
                penalty_prosodic_med = sc.penalty_prosodic_med
            )
        except Exception as e:
            logger.error(f"Error parsing NLP params: {e}")
            raise e
    
    def get_cv_config(self) -> CVConfig:
        """Returns CV analysis parameters from params.yaml"""
        try:
            # Assuming your params.yaml has a top-level key 'cv_analysis'
            cv_params = self.params.cv_analysis
            
            return CVConfig(
                # General
                min_detection_confidence=cv_params.general.min_detection_confidence,
                min_tracking_confidence=cv_params.general.min_tracking_confidence,
                video_fps_fallback=cv_params.general.video_fps_fallback,
                
                # Head
                head_movement_threshold=cv_params.head_movement.movement_threshold_px,
                head_facing_threshold=cv_params.head_movement.facing_threshold,
                head_pitch_neutral_pct=cv_params.head_movement.pitch_neutral_pct,
                head_smoothing_window=cv_params.head_movement.smoothing_window,
                head_major_event_duration=cv_params.head_movement.major_event_duration,
                head_time_gap_tolerance=cv_params.head_movement.time_gap_tolerance,
                
                # Eye
                eye_calibration_time=cv_params.eye_gaze.calibration_duration,
                eye_movement_threshold=cv_params.eye_gaze.movement_threshold,
                eye_min_event_duration=cv_params.eye_gaze.min_event_duration,
                eye_up_sensitivity_multiplier=cv_params.eye_gaze.up_sensitivity_multiplier,
                
                # Expression - General
                expr_calibration_frames=cv_params.expression.calibration_frames,
                expr_frame_skip=cv_params.expression.frame_skip,
                
                # Expression - Thresholds
                expr_thresh_happy=cv_params.expression.thresh_happy,
                expr_thresh_surprise=cv_params.expression.thresh_surprise,
                
                # Expression - Sensitivity
                expr_sensitivity_lip=cv_params.expression.sensitivity_lip_thickness,
                expr_sensitivity_brow_squeeze=cv_params.expression.sensitivity_brow_squeeze,
                expr_sensitivity_brow_drop=cv_params.expression.sensitivity_brow_drop,
                
                # Expression - Defaults
                expr_default_lip_thickness=cv_params.expression.default_lip_thickness,
                expr_default_brow_squeeze=cv_params.expression.default_brow_squeeze,
                expr_default_brow_drop=cv_params.expression.default_brow_drop
            )
        except Exception as e:
            # Assuming 'logger' is imported in this file
            logger.error(f"Error parsing CV params: {e}")
            raise e
        
    def get_code_analysis_config(self) -> CodeAnalysisConfig:
        """Returns Code Analysis AI parameters and weights from params.yaml"""
        try:
            # Assuming your params.yaml has a top-level key 'code_analysis'
            code_params = self.params.code_analysis
            
            return CodeAnalysisConfig(
                provider=code_params.provider,
                model_name=code_params.model_name,
                base_url=code_params.base_url,
                max_tokens=code_params.max_tokens,
                temperature=code_params.temperature,
                weights=code_params.weights  
            )
        except Exception as e:
            # Assuming 'logger' is imported
            logger.error(f"Error parsing Code Analysis params: {e}")
            raise e
        
    def get_report_generation_config(self) -> ReportGenerationConfig:
        
        # params.yaml se 'report_generation' section uthaya
        report_params = self.params.report_generation 
        llm_params = report_params.llm
        prompt_params = report_params.prompts

        config = ReportGenerationConfig(
            provider=llm_params.provider,
            model_name=llm_params.model_name,
            base_url=llm_params.base_url,
            temperature=float(llm_params.temperature),
            max_tokens=int(llm_params.max_tokens),
            
            # Prompts map kar rahay hain
            system_prompt=prompt_params.system_role,
            user_prompt_template=prompt_params.user_template
        )

        return config

    

    def get_confidence_training_config(self) -> ConfidenceTrainingConfig:
        config = self.config.confidence_model_training
        params = self.params.confidence_model_params
        
        # Artifacts directory create karain
        os.makedirs(config.root_dir, exist_ok=True)
        # Models directory create karain (jahan model save hoga)
        os.makedirs(os.path.dirname(config.model_save_path), exist_ok=True)

        return ConfidenceTrainingConfig(
            root_dir=Path(config.root_dir),
            dataset_path=Path(config.dataset_path),
            model_save_path=Path(config.model_save_path),
            scaler_save_path=Path(config.scaler_save_path),
            n_estimators=params.n_estimators,
            random_state=params.random_state,
            test_size=params.test_size
        )
    
 