"""Debug environment overrides"""
import os
from unittest.mock import patch
from app.config import Config

# Test production environment
with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
    Config._instance = None
    Config._loaded = False
    
    # Add debug
    original_apply_env = Config._apply_environment_overrides
    
    def debug_apply_env(self):
        print(f"DEBUG: Before env overrides - logging.level = {self.logging.level}")
        print(f"DEBUG: ENVIRONMENT = {self.ENVIRONMENT}")
        print(f"DEBUG: is_production() = {self.is_production()}")
        result = original_apply_env(self)
        print(f"DEBUG: After env overrides - logging.level = {self.logging.level}")
        return result
    
    Config._apply_environment_overrides = debug_apply_env
    
    config = Config()
    
    print(f"\nFinal values:")
    print(f"ENVIRONMENT: {config.ENVIRONMENT}")
    print(f"logging.level: {config.logging.level}")
    print(f"logging.format: {config.logging.format}")
    print(f"logging.use_colors: {config.logging.use_colors}")
    print(f"monitoring.enabled: {config.monitoring.enabled}")