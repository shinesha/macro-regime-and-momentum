import yaml
import os

def load_config(config_path="config.yaml"):
    if not os.path.exists(config_path):
        # Fallback to parent directory if running from src/
        config_path = "../config.yaml"
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# Global configuration instance
CONFIG = load_config()