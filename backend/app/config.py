from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    remote_db_url: str
    local_db_url: str
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "vnd_documents"
    gemini_api_key: str
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()