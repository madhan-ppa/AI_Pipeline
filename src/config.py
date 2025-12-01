"""
Configuration settings for the AI Pipeline Project.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the AI Pipeline."""
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = "openai/gpt-oss-20b:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # OpenWeatherMap Configuration
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "")
    OPENWEATHERMAP_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    
    # LangSmith Configuration
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "ai-pipeline-project")
    LANGSMITH_ORGANIZATION: str = os.getenv("LANGSMITH_ORGANIZATION", "default")
    
    # Qdrant Configuration
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL", None)
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None)
    QDRANT_COLLECTION_NAME: str = "ai_pipeline_docs"
    
    # Vector Database Configuration  
    EMBEDDING_DIMENSION: int = 384  # For local sentence-transformers (all-MiniLM-L6-v2)
    VECTOR_SEARCH_LIMIT: int = 5
    
    # PDF Processing Configuration
    PDF_CHUNK_SIZE: int = 1000
    PDF_CHUNK_OVERLAP: int = 200
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 30

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required_keys = [
            "OPENROUTER_API_KEY",
            "OPENWEATHERMAP_API_KEY"
        ]
        
        missing_keys = [key for key in required_keys if not getattr(cls, key)]
        
        if missing_keys:
            print(f"Missing required environment variables: {missing_keys}")
            return False
        
        if cls.LANGSMITH_TRACING and not cls.LANGSMITH_API_KEY:
            print("Warning: LangSmith tracing is enabled but no API key provided")
        
        return True
