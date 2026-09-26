"""
Configuration settings for Agentic AI STLC Pipeline.

Uses Pydantic Settings for environment variable management with validation.
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== NVIDIA Nemotron 3 Ultra 550B =====
    nemotron_api_key: SecretStr = Field(
        default="",
        description="API key for NVIDIA Nemotron 3 Ultra 550B",
    )
    nemotron_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="Base URL for Nemotron API",
    )
    nemotron_model: str = Field(
        default="nvidia/nemotron-3-ultra",
        description="Nemotron model identifier",
    )
    nemotron_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM generation",
    )
    nemotron_max_tokens: int = Field(
        default=8192,
        ge=1,
        le=32768,
        description="Maximum tokens for LLM response",
    )

    # ===== Jira Cloud REST API v3 =====
    jira_base_url: str = Field(
        default="",
        description="Jira Cloud instance base URL (e.g., https://your-domain.atlassian.net)",
    )
    jira_email: str = Field(
        default="",
        description="Jira account email for Basic Auth",
    )
    jira_api_token: SecretStr = Field(
        default="",
        description="Jira API token for authentication",
    )
    jira_project_key: str = Field(
        default="",
        description="Jira project key for defect creation",
    )
    jira_issue_type: str = Field(
        default="Bug",
        description="Jira issue type for defects",
    )

    # ===== GitHub Actions =====
    github_token: SecretStr = Field(
        default="",
        description="GitHub Personal Access Token with repo and workflow scopes",
    )
    github_repo_owner: str = Field(
        default="beepakbehera",
        description="GitHub repository owner",
    )
    github_repo_name: str = Field(
        default="agentic-ai-stlc-pipeline",
        description="GitHub repository name",
    )
    github_workflow_id: str = Field(
        default="agentic_tests.yml",
        description="GitHub Actions workflow file name",
    )

    # ===== Vector DB / RAG =====
    vector_db_path: str = Field(
        default="./data/vector_db",
        description="Path to local vector database (ChromaDB)",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model for RAG retrieval",
    )
    chunk_size: int = Field(
        default=1000,
        description="Chunk size for document splitting",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Chunk overlap for document splitting",
    )
    top_k_retrieval: int = Field(
        default=5,
        description="Number of top documents to retrieve",
    )

    # ===== MCP Selector Self-Healing =====
    mcp_server_url: str = Field(
        default="http://localhost:3000",
        description="MCP server URL for selector healing",
    )
    mcp_timeout: int = Field(
        default=30,
        description="MCP request timeout in seconds",
    )

    # ===== Pipeline Execution =====
    pipeline_timeout: int = Field(
        default=3600,
        description="Maximum pipeline execution time in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retries for failed stages",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # ===== Optional: LangSmith Tracing =====
    langsmith_api_key: Optional[SecretStr] = Field(
        default=None,
        description="LangSmith API key for tracing (optional)",
    )
    langsmith_project: str = Field(
        default="agentic-ai-stlc-pipeline",
        description="LangSmith project name",
    )
    langsmith_endpoint: str = Field(
        default="https://apac.api.smith.langchain.com",
        description="LangSmith API endpoint (US: https://api.smith.langchain.com, APAC: https://apac.api.smith.langchain.com)",
    )
    langsmith_tracing: bool = Field(
        default=True,
        description="Enable LangSmith tracing",
    )

    # ===== Application Under Test & Environment =====
    base_url: str = Field(
        default="https://www.saucedemo.com/",
        description="Base URL for the application under test",
    )
    api_url: str = Field(
        default="",
        description="API URL for the application under test",
    )
    browser: str = Field(
        default="chromium",
        description="Browser for automated testing (chromium, firefox, webkit)",
    )
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode",
    )
    environment: str = Field(
        default="staging",
        description="Target execution environment (staging, production, development)",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export commonly used settings
settings = get_settings()