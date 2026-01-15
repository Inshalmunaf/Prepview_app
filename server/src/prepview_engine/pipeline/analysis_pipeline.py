import os
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import ConfigurationManager
from prepview_engine.database.db_connector import DatabaseConnector

# Import Components
from prepview_engine.components.preprocessing import PreprocessingComponent
from prepview_engine.components.cv_analyzer import CVAnalyzerComponent
from prepview_engine.components.nlp_analyzer import NLPAnalyzerComponent

class AnalysisPipeline:
    def __init__(self):
        """
        Initializes the entire engine.
        Components are initialized once with Config.
        """
        logger.info("Initializing Analysis Pipeline Components...")
        
        self.config_manager = ConfigurationManager()
        
        # 1. Database Connection
        self.db = DatabaseConnector(self.config_manager.get_database_config())
        
        # 2. Initialize Preprocessor (Reusable)
        self.preprocessor = PreprocessingComponent(config=self.config_manager.get_preprocessing_config())
        
        # 3. Initialize AI Models (Reusable)
        logger.info("Loading CV Model Configuration...")
        self.cv_analyzer = CVAnalyzerComponent(config=self.config_manager.get_cv_config())
        
        logger.info("Loading NLP Model Configuration...")
        self.nlp_analyzer = NLPAnalyzerComponent(config=self.config_manager.get_nlp_config())
        
        logger.info("Pipeline Components Ready.")

    def process_chunk(self, session_id: str, question_id: str, video_path: str):
        """
        Processes a SINGLE video chunk from start to finish.
        Flow: Video -> Audio -> CV Analysis + NLP Analysis -> Database Storage
        """
        logger.info(f"[START] Processing Chunk: {question_id} for Session: {session_id}")
        
        # Validation
        if not os.path.exists(video_path):
            logger.error(f"Video file not found at: {video_path}")
            return False

        try:
            # --- STEP 1: PREPROCESSING (Extract Audio) ---
            logger.info("Step 1: Extracting Audio...")
            audio_path = self.preprocessor.run(video_path)
            
            if not audio_path or not os.path.exists(audio_path):
                raise Exception("Audio extraction failed.")

            # --- STEP 2: CV ANALYSIS (Visuals) ---
            logger.info("Step 2: Running CV Analysis...")
            cv_results = self.cv_analyzer.run(video_path)
            
            # --- STEP 3: NLP ANALYSIS (Speech & Text) ---
            logger.info("Step 3: Running NLP Analysis...")
            nlp_results = self.nlp_analyzer.run(str(audio_path))

            # --- STEP 4: STORAGE (Save to DB) ---
            logger.info("Step 4: Saving Results to Database...")
            
            save_success = self.db.save_chunk_results(
                session_id=session_id,
                question_id=question_id,
                nlp_data=nlp_results,
                cv_data=cv_results
                
            )

            if save_success:
                logger.info(f"[SUCCESS] Chunk {question_id} processed and stored successfully.")
                return True
            else:
                logger.error(f"[FAILURE] Analysis done but Database Save failed for {question_id}.")
                return False

        except Exception as e:
            logger.error(f"Pipeline Crashed for {question_id}: {e}")
            import traceback
            traceback.print_exc()
            return False