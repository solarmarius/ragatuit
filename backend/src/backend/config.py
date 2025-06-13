from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    CANVAS_CLIENT_ID: str
    CANVAS_CLIENT_SECRET: str
    CANVAS_REDIRECT_URI: str
    JWT_SECRET: str
    CANVAS_DOMAIN: str # Added for Canvas API and auth URLs

    # JWT Settings from new subtask
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Example of a default value if needed for other settings
    # API_V1_STR: str = "/api/v1"

    # Configure Pydantic to load from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

# Instantiate settings early to catch missing env vars at startup (optional)
# settings = Settings()
