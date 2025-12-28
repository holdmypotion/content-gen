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

    # Google Generative AI
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-2.5-flash"

    # Prompts
    IDEA_PROMPT_TEMPLATE_PATH: str = "prompts/idea_template.jinja2"
    POST_PROMPT_TEMPLATE_PATH: str = "prompts/post_template.jinja2"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
