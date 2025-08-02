"""Debug config loading"""
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open

# Clear any existing instance
from app.config import Config
Config._instance = None
Config._loaded = False

config_data = {
    "slack": {"request_timeout": 45, "max_retries": 5},
    "openai": {"base_delay": 2.0},
    "emoji": {"cache_ttl": 7200},
}

mock_file_content = json.dumps(config_data)

with patch.dict(os.environ, {"CONFIG_FILE": "/tmp/test_config.json"}, clear=True):
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            # Add debug logging
            original_load_from_file = Config._load_from_file
            original_apply_dict_config = Config._apply_dict_config
            
            def debug_load_from_file(self, config_file):
                print(f"DEBUG: _load_from_file called with {config_file}")
                result = original_load_from_file(self, config_file)
                print(f"DEBUG: _load_from_file completed")
                return result
            
            def debug_apply_dict_config(self, config_dict):
                print(f"DEBUG: _apply_dict_config called with {config_dict}")
                result = original_apply_dict_config(self, config_dict)
                print(f"DEBUG: After apply_dict_config, slack.request_timeout = {self.slack.request_timeout}")
                return result
            
            Config._load_from_file = debug_load_from_file
            Config._apply_dict_config = debug_apply_dict_config
            
            config = Config()
            
            print(f"\nFinal values:")
            print(f"CONFIG_FILE env var: {os.getenv('CONFIG_FILE')}")
            print(f"config.CONFIG_FILE: {config.CONFIG_FILE}")
            print(f"slack.request_timeout: {config.slack.request_timeout}")
            print(f"slack.max_retries: {config.slack.max_retries}")
            print(f"openai.base_delay: {config.openai.base_delay}")
            print(f"emoji.cache_ttl: {config.emoji.cache_ttl}")