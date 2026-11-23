"""Settings from .env and the environment."""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Each field reads the environment variable with the same name in capitals."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )

    api_host: str
    ingest_host: str
    project_short_code: str
    dsp_user: str
    dsp_pwd: SecretStr
    ontology_name: str = "SGB"
    item_set_id: str = "10780"
    omeka_api_url: str = "https://omeka.unibe.ch/api/"
    key_identity: str | None = None
    key_credential: str | None = None
    http_timeout: float = 30
    ingest_timeout: float = 600
    dsp_retries: int = 20

    @field_validator("key_identity", "key_credential", mode="before")
    @classmethod
    def _empty_is_none(cls, value: str | None) -> str | None:
        # requests sends an empty string, but leaves out None.
        return value or None

    @field_validator(
        "api_host", "ingest_host", "project_short_code", "dsp_user", "dsp_pwd"
    )
    @classmethod
    def _not_empty(cls, value: str | SecretStr) -> str | SecretStr:
        text = value.get_secret_value() if isinstance(value, SecretStr) else value
        if not text.strip():
            raise ValueError("must not be empty")
        return value
