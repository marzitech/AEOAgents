from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # WordPress.com OAuth2
    wordpress_site: str = ""           # e.g. marziblogs1.wordpress.com
    wordpress_client_id: str = ""      # OAuth app Client ID
    wordpress_client_secret: str = ""  # OAuth app Client Secret
    wordpress_access_token: str = ""   # OAuth2 bearer token (obtained via auth flow)

    # Gemini — gemini-2.5-* is closed to new API keys; override with GEMINI_MODEL if needed
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"   # 3.8-flash was failing ~75% with 503 "high demand" (2026-10-06)
    gemini_image_model: str = "gemini-3.1-flash-image"

    # SerpApi (optional — enables competitive gap research)
    serpapi_key: str = ""

    # Hosting — AWS S3 + CloudFront (stack: infra/static-site.yaml, aeo-marzi-life)
    s3_bucket: str = "aeo-marzi-life-904233100956"
    cloudfront_distribution_id: str = "E321IIF074LQON"

    # Site
    site_url: str = "https://d12xiu8vvi5sts.cloudfront.net"
    site_name: str = "Marzi Life Blog"
    organization_name: str = "Marzi"
    default_author: str = "Marzi Life"

    # Generation
    num_variations: int = 3
    dedup_similarity_threshold: float = 0.85

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
