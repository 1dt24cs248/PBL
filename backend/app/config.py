from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./pbl.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    bcrypt_rounds: int = 12
    demo_student_usns: str = "1DT24CS248,1DT24CS001,1DT24CS002,1DT24CS003,1DT24CS004"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
