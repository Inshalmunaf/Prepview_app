import uvicorn
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from prepview_engine.utils.common import logger
from prepview_engine.pipeline.analysis_pipeline import AnalysisPipeline
from prepview_engine.config.configuration import ConfigurationManager
from prepview_engine.database.db_connector import DatabaseConnector
from prepview_engine.components.result_aggregator import ResultAggregator
from prepview_engine.components.report_generator import ReportGenerator

app = FastAPI(title="PrepView AI Engine (Pipeline Mode)")

analysis_pipeline = None
db_connector = None
aggregator = None      
report_generator = None

# ==========================================
# 1. SETUP ON STARTUP
# ==========================================
@app.on_event("startup")
async def startup_event():
    global analysis_pipeline, db_connector, aggregator, report_generator
    
    logger.info(" Starting PrepView AI Engine...")

    try:
        # 1. Init Config & DB
        config_manager = ConfigurationManager()
        db_config = config_manager.get_database_config()
        db_connector = DatabaseConnector(config=db_config)
        
        # 2. Init Pipeline (Chunk Analysis ke liye)
        logger.info("⚙️ Initializing Pipeline...")
        analysis_pipeline = AnalysisPipeline()

        # 3. 👇 INIT REPORTING COMPONENTS (Ye naya hissa hai)
        logger.info("📊 Initializing Report Components...")
        aggregator = ResultAggregator(db_connector=db_connector)
        
        report_config = config_manager.get_report_generation_config()
        report_generator = ReportGenerator(config=report_config)
        
        logger.info(" All Systems Ready!")
        
    except Exception as e:
        logger.critical(f" Initialization Failed: {e}")
        raise e
# ==========================================
# 2. REQUEST BODY
# ==========================================
class AnalyzeRequest(BaseModel):
    session_id: str
    question_id: str
    video_file_path: str

class CodeAnalyzeRequest(BaseModel):
    session_id: str
    question_id: str
    code: str
    language: str
    question_title: str
    question_description: str

class ReportRequest(BaseModel):
    session_id: str
    user_id: str

# ==========================================
# 3. BACKGROUND TASK (Simplified)
# ==========================================
# --- Task A: Analyze Chunk 
def process_video_task(request: AnalyzeRequest):
    try:
        if analysis_pipeline:
            analysis_pipeline.process_chunk(request.session_id, request.question_id, request.video_file_path)
    except Exception as e:
        logger.error(f"❌ Pipeline Error: {e}", exc_info=True)

def process_code_task(request: CodeAnalyzeRequest):
    try:
        if analysis_pipeline:
            analysis_pipeline.process_code_chunk(
                session_id=request.session_id,
                question_id=request.question_id,
                code=request.code,
                language=request.language,
                question_title=request.question_title,
                question_description=request.question_description,
                video_path_str=getattr(request, 'video_file_path', ""), # Safely handles video path
            )
    except Exception as e:
        logger.error(f" Code Pipeline Error: {e}", exc_info=True)

# --- Task B: Generate Report 
def generate_report_task(request: ReportRequest):
    """
    1. Aggregate Data
    2. Call LLM for Feedback
    3. Save Final Report to DB
    """
    try:
        logger.info(f"📑 [START] Generating Report for Session: {request.session_id}")
        
        # Step 1: Aggregate
        if not aggregator:
            logger.error("❌ Aggregator not initialized")
            return
            
        logger.info("🔄 Aggregating Data...")
        aggregated_data = aggregator.aggregate_session(request.session_id)
        
        if not aggregated_data:
            logger.error(f"❌ No data found for session {request.session_id}. Cannot generate report.")
            return

        # Step 2: Generate AI Feedback
        if not report_generator:
            logger.error("❌ Report Generator not initialized")
            return

        logger.info("🤖 Generating AI Feedback (LLM Call)...")
        feedback_text = report_generator.generate_feedback(aggregated_data)

        # Step 3: Save to DB
        logger.info("💾 Saving Final Report...")
        
        nlp_data = aggregated_data.get("nlp_aggregate", {})
        cv_data = aggregated_data.get("cv_aggregate", {})

        success = db_connector.save_final_report(
            session_id=request.session_id,
            user_id=request.user_id,
            nlp_agg=nlp_data,
            cv_agg=cv_data,
            feedback_text=feedback_text
        )

        if success:
            logger.info(f"🎉 REPORT GENERATED & SAVED for Session: {request.session_id}")
        else:
            logger.error("❌ Report generated but DB Save Failed.")

    except Exception as e:
        logger.error(f"❌ Report Generation Failed: {e}", exc_info=True)
# ==========================================
# 4. API ENDPOINT
# ==========================================
@app.post("/analyze_chunk")
async def analyze_chunk(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    
    # Basic Input Check
    if not request.session_id or not request.question_id:
        raise HTTPException(status_code=400, detail="Missing IDs")

    # Background Task Add
    background_tasks.add_task(process_video_task, request)

    return {
        "status": "processing_started",
        "message": "Request received. Pipeline is processing in background.",
        "session_id": request.session_id
    }

@app.post("/analyze_code")
async def analyze_code(request: CodeAnalyzeRequest, background_tasks: BackgroundTasks):
    
    # Input Check
    if not request.session_id or not request.question_id:
        raise HTTPException(status_code=400, detail="Missing IDs")

    # Background Task Add
    background_tasks.add_task(process_code_task, request)

    return {
        "status": "processing_started",
        "message": "Code received. AI Analysis is running in background.",
        "session_id": request.session_id
    }

@app.post("/generate_finalreport")
async def generate_finalreport(request: ReportRequest): 
    """
    Ab hum User ko wait karwayenge taakay jab wo aglay page par jaye 
    toh Report DB mein majood ho.
    """
    # Validation
    if not request.session_id or not request.user_id:
        raise HTTPException(status_code=400, detail="Missing session_id or user_id")

    try:
        # 👇 DIRECT CALL (No Background Task)
        # Ye line ab code ko rok kar rakhegi jab tak report ban na jaye
        generate_report_task(request) 

        return {
            "status": "success",
            "message": "Report Generated & Saved", # ✅ Ab ye sach hai
            "session_id": request.session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    # reload=False hi rakhein kyunki models heavy hain
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)