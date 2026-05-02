import os
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import ConfigurationManager
from prepview_engine.database.db_connector import DatabaseConnector

# Import Components
from prepview_engine.components.preprocessing import PreprocessingComponent
from prepview_engine.components.cv_analyzer import CVAnalyzerComponent
from prepview_engine.components.nlp_analyzer import NLPAnalyzerComponent
from prepview_engine.components.code_analyzer import CodeAnalyzer

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

        logger.info("Loading Code Configuration...")
        self.code_analyzer = CodeAnalyzer(config=self.config_manager.get_code_analysis_config())
        
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
    
    def process_code_chunk(self, session_id: str, question_id: str, code: str, language: str, question_title: str, question_description: str, video_path_str: str):
        """
        Processes a SINGLE coding question chunk.
        Flow: Code string -> LLaMA-3 Code Evaluation -> Database Storage
        """
        logger.info(f"[START] Processing Code Chunk: {question_id} for Session: {session_id}")
        
        # Note: video_path_str is available here if you decide to add Video/CV analysis to coding questions later.
        if video_path_str:
            logger.debug(f"Video path received but skipping video analysis for coding chunk: {video_path_str}")

        if not code or code.strip() == "":
            logger.error(f"Empty code received for question {question_id}")
            return False

        try:
            # Combine title and description for the AI Prompt
            full_question_context = f"Title: {question_title}\nDescription: {question_description}"

            # --- STEP 1: AI CODE ANALYSIS ---
            logger.info("Step 1: Running Code Analysis via AI...")
            
            # 🌟 UPDATE: Using the new .run() standard interface
            code_results = self.code_analyzer.run(
                question=full_question_context,
                code=code,
                language=language,
                video_path_str=video_path_str,
            )

            if not code_results.get("success"):
                logger.error(f"Code Evaluation Failed: {code_results.get('error_message')}")
                # Agar API crash hui hai, toh hum DB mein save nahi karenge
                return False

            # --- STEP 2: STORAGE (Save to DB) ---
            logger.info("Step 2: Saving Code Evaluation Results to Database...")
            
            # Note: Aapko apni db_connector file mein 'save_code_results' ka function banana hoga
            save_success = self.db.save_code_results(
                session_id=session_id,
                question_id=question_id,
                code_data=code_results
            )

            if save_success:
                logger.info(f"[SUCCESS] Code Chunk {question_id} processed and stored successfully.")
                return True
            else:
                logger.error(f"[FAILURE] Analysis done but Database Save failed for {question_id}.")
                return False

        except Exception as e:
            logger.error(f"Code Pipeline Crashed for {question_id}: {e}")
            import traceback
            traceback.print_exc()
            return False