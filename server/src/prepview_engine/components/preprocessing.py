import os
import subprocess  # 👈 MoviePy ki jagah ye use karenge
from pathlib import Path
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import PreprocessingConfig

class PreprocessingComponent:
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        logger.info("PreprocessingComponent Initialized.") # ⚠️ Emoji hata diya (Windows Safety)

    def extract_audio(self, video_path: Path) -> Path:
        """
        Uses Direct FFmpeg command to extract audio.
        Much more robust for incomplete WebM files than MoviePy.
        """
        try:
            video_name = video_path.stem
            os.makedirs(self.config.temp_video_path, exist_ok=True)
            
            audio_file_name = f"{video_name}_audio.wav"
            audio_file_path = Path(self.config.temp_video_path) / audio_file_name
            
            logger.info(f"Starting audio extraction for: {video_path.name}")
            
            # 👇 ROBUST FFmpeg Command
            # Ye command seedha FFmpeg ko bolti hai: "Video ignore karo, sirf Audio nikal kar save karo"
            command = [
                "ffmpeg",
                "-y",                   # Overwrite if exists
                "-i", str(video_path),  # Input File
                "-vn",                  # No Video (Sirf Audio chahiye)
                "-acodec", "pcm_s16le", # WAV standard format
                "-ar", "44100",         # Audio Rate (Standard)
                "-ac", "2",             # Channels (Stereo)
                str(audio_file_path)    # Output File
            ]

            # Subprocess run karein (Bina shell=True ke taakay secure rahay)
            # stderr=subprocess.PIPE se hum faltu logs chupayenge taakay console ganda na ho
            process = subprocess.run(
                command, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            logger.info(f"Audio saved to: {audio_file_path}")
            return audio_file_path
            
        except subprocess.CalledProcessError as e:
            # Agar FFmpeg fail ho jaye toh uska error decode karke dikhayen
            error_message = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            logger.error(f"FFmpeg failed: {error_message}")
            raise RuntimeError(f"FFmpeg conversion failed: {error_message}")

        except Exception as e:
            logger.error(f"Error during audio extraction: {e}")
            raise e

    def run(self, video_path_str: str) -> Path:
        video_path = Path(video_path_str)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Original video file not found at: {video_path}")

        logger.info(f"--- Processing Video: {video_path.name} ---")
        
        # 1. Extract Audio
        audio_path = self.extract_audio(video_path)
        
        return audio_path