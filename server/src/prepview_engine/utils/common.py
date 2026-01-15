import os
import yaml
import logging
from box import ConfigBox 
import sys
from pydantic import BaseModel
from pathlib import Path
from typing import Any

# --- Central Logger ---
log_dir = "logs"
log_filepath = os.path.join(log_dir, "running_logs.log")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath), 
        logging.StreamHandler(sys.stdout)
    ]
)

# ham logger ko import kar lain gay har file mai
logger = logging.getLogger("prepview_engine_logger")


# --- YAML File Reader Utility ---
def read_yaml(path_to_yaml: Path) -> ConfigBox:
    """
    Reads a YAML file and returns its content as a ConfigBox object.
    
    Args:
        path_to_yaml (Path): Path to the YAML file.
        
    Returns:
        ConfigBox: A ConfigBox object (acts like a dictionary).
    """
    try:
        with open(path_to_yaml) as yaml_file:
            content = yaml.safe_load(yaml_file)
            logger.info(f"YAML file '{path_to_yaml}' loaded successfully.")
            return ConfigBox(content)
    except Exception as e:
        logger.error(f"Error reading YAML file '{path_to_yaml}': {e}")
        raise