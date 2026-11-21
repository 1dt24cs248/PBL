from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = "sqlite:///./pbl.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    bcrypt_rounds: int = 12
    demo_student_usns: str = ""
    nav_metres_per_pixel: float = Field(default=0.06, gt=0)
    nav_stairs_metres_per_floor: float = Field(default=12.0, gt=0)
    nav_lift_metres_per_floor: float = Field(default=8.0, gt=0)
    nav_lift_wait_seconds: float = Field(default=20.0, ge=0)
    nav_walking_speed_mps: float = Field(default=1.2, gt=0)
    period_hours: float = Field(default=55 / 60, gt=0)
    energy_tariff_inr_per_kwh: float = Field(default=8.5, ge=0)
    standby_fraction: float = Field(default=0.0, ge=0, le=1)
    periods_per_day: int = Field(default=7, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
