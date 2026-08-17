from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()