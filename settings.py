from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Settings for GitHub Service.
    This class uses Pydantic to manage configuration settings, including
    environment variables and default values.
    """
    
    gitlab_access_token: str = Field(
        default=None,
        description="GITLAB_ACCESS_TOKEN"
    )
    
    """Access Token for GitLab API requests."""
    
    gitlab_base_url: str = Field(
        default="https://gitlab.com",
        description="GITLAB_BASE_URL",
    )
    
    """Base URL of GitLab provider"""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        exitra = "allow"

settings = Settings()