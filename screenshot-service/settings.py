from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_prefix: str = "link-previews/"
    public_base_url: str = ""

    viewport_width: int = 1280
    viewport_height: int = 720
    thumbnail_width: int = 400
    thumbnail_height: int = 225

    screenshot_timeout_ms: int = 30000
    navigation_timeout_ms: int = 45000

    allowed_hosts: str = ""

    @property
    def host_allowlist(self) -> set[str]:
        if not self.allowed_hosts.strip():
            return set()
        return {h.strip().lower() for h in self.allowed_hosts.split(",") if h.strip()}


settings = Settings()
