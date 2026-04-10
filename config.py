from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    llm_model: str = "llama-3.3-70b-versatile"
    confidence_threshold: float = 0.75

    redis_host: str = "localhost"
    redis_port: int = 6379
    use_redis: bool = False

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    use_neo4j: bool = False

    class Config:
        env_file = ".env"


settings = Settings()