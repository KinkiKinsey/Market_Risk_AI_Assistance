"""
Configuration file for the Investment Analysis Pipeline Web App
"""

import os
from typing import Dict, Any

class Config:
    """Configuration class for the web app"""
    
    # App settings
    APP_NAME = "Investment Analysis Pipeline"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "AI-powered investment analysis pipeline with noise filtering and impact chain visualization"
    
    # Streamlit settings
    STREAMLIT_PAGE_TITLE = "🚀 Investment Analysis Pipeline"
    STREAMLIT_PAGE_ICON = "🚀"
    STREAMLIT_LAYOUT = "wide"
    
    # Default values
    DEFAULT_USER_ID = "jingxi"
    DEFAULT_TICKER = "COIN"
    DEFAULT_QUESTION = "In late July, Coinbase reported Q2 2025 earnings that missed expectations:"
    
    # UI settings
    CHAT_BOX_HEIGHT = 120
    MAX_RESULT_LENGTH = 200
    AUTO_REFRESH_INTERVAL = 5  # seconds
    
    # Pipeline settings
    PIPELINE_STEPS = [
        {
            "name": "noise_filter",
            "title": "🔍 Noise Filter AI",
            "description": "Analyzing investment noise...",
            "color": "#1f77b4"
        },
        {
            "name": "impaction_ai",
            "title": "🎯 Impaction AI",
            "description": "Analyzing market impact...",
            "color": "#ff7f0e"
        },
        {
            "name": "chain_of_thought",
            "title": "🔗 Chain of Thought AI",
            "description": "Generating impact chain...",
            "color": "#2ca02c"
        }
    ]
    
    # Mermaid.js settings
    MERMAID_THEME = "default"
    MERMAID_CHART_HEIGHT = 500
    MERMAID_DOWNLOAD_FORMATS = ["svg", "png"]
    
    # Error messages
    ERROR_MESSAGES = {
        "noise_filter": "❌ Error in Noise Filter AI",
        "impaction_ai": "❌ Error in Impaction AI",
        "chain_of_thought": "❌ Error in Chain of Thought AI",
        "general": "❌ An error occurred during analysis"
    }
    
    # Success messages
    SUCCESS_MESSAGES = {
        "noise_filter": "✅ Noise Filter AI completed successfully!",
        "impaction_ai": "✅ Impaction AI completed successfully!",
        "chain_of_thought": "✅ Chain of Thought AI completed successfully!",
        "pipeline_complete": "🎉 Pipeline Complete!"
    }
    
    # Status colors
    STATUS_COLORS = {
        "waiting": "#6c757d",
        "running": "#ffc107",
        "success": "#28a745",
        "error": "#dc3545"
    }
    
    @classmethod
    def get_pipeline_step(cls, step_name: str) -> Dict[str, Any]:
        """Get pipeline step configuration by name"""
        for step in cls.PIPELINE_STEPS:
            if step["name"] == step_name:
                return step
        return None
    
    @classmethod
    def get_error_message(cls, step_name: str) -> str:
        """Get error message for a specific step"""
        return cls.ERROR_MESSAGES.get(step_name, cls.ERROR_MESSAGES["general"])
    
    @classmethod
    def get_success_message(cls, step_name: str) -> str:
        """Get success message for a specific step"""
        return cls.SUCCESS_MESSAGES.get(step_name, "")
    
    @classmethod
    def get_status_color(cls, status: str) -> str:
        """Get color for a specific status"""
        return cls.STATUS_COLORS.get(status, "#6c757d")

# Environment-specific configurations
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = "INFO"

# Configuration factory
def get_config(environment: str = None) -> Config:
    """Get configuration based on environment"""
    if environment is None:
        environment = os.getenv("FLASK_ENV", "development")
    
    if environment == "production":
        return ProductionConfig()
    else:
        return DevelopmentConfig()

# Default configuration
config = get_config()
