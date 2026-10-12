from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # AI Provider
    AI_PROVIDER: str = Field(default="groq")
    GROQ_API_KEY: str = Field(default="")
    ANTHROPIC_API_KEY: str = Field(default="")
    GOOGLE_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    CLAUDE_MODEL: str = Field(default="claude-sonnet-4-6")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")

    # Target application under test — point this at localhost or a live site via .env
    BASE_URL: str = Field(default="http://localhost:3000")

    # Target app login (used by generated tests + self-healing DOM analysis).
    # Leave blank if the target app needs no login.
    LOGIN_USERNAME: str = Field(default="")
    LOGIN_PASSWORD: str = Field(default="")
    LOGIN_USERNAME_SELECTOR: str = Field(default='input[name="username"]')
    LOGIN_PASSWORD_SELECTOR: str = Field(default='input[name="password"]')
    LOGIN_SUBMIT_SELECTOR: str = Field(default='button[type="submit"]')
    LOGIN_SUCCESS_URL_PATTERN: str = Field(default="")

    # Platform auth (login to this Streamlit app, not the target app under test)
    PLATFORM_USERNAME: str = Field(default="admin")
    PLATFORM_PASSWORD: str = Field(default="demo1234")

    # Settings
    HEADLESS_BROWSER: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
