from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # FastAPI
    APP_NAME: str = "Content Generator API"
    DEBUG: bool = True

    # Celery & Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "content_gen"

    # Google Generative AI
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-2.5-flash"

    # OpenAI GPT
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1"

    # Prompts
    IDEA_PROMPT_TEMPLATE_PATH: str = "prompts/idea_template.jinja2"
    POST_PROMPT_TEMPLATE_PATH: str = "prompts/post_template.jinja2"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
