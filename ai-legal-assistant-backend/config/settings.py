import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    
    # Google Gemini API Configuration
    gemini_api_key: str
    
    # Database Configuration
    database_url: str
    
    # Document Processing Configuration
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    supported_file_types: list = [".pdf", ".docx", ".txt"]
    
    # Embedding Configuration
    embedding_model: str = "models/embedding-001"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # RAG Configuration
    max_context_length: int = 4000
    temperature: float = 0.7
    top_k: int = 5
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()