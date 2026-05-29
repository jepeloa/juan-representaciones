from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    DB_HOST: str = 'mysql'
    DB_PORT: int = 3306
    DB_USER: str = 'catalogo'
    DB_PASSWORD: str = 'catalogo'
    DB_NAME: str = 'catalogo'

    JWT_SECRET: str = 'change-me-in-prod'
    JWT_ALGORITHM: str = 'HS256'
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    INITIAL_ADMIN_USER: str = 'juan'
    INITIAL_ADMIN_PASSWORD: str = 'juan2026'

    IMAGES_PATH: str = '/srv/images'

    CORS_ORIGINS: str = '*'

    # SMTP settings (optional — if SMTP_HOST is empty, emails are only logged)
    SMTP_HOST: str = ''
    SMTP_PORT: int = 587
    SMTP_USER: str = ''
    SMTP_PASSWORD: str = ''
    SMTP_FROM: str = ''
    SMTP_USE_TLS: bool = True

    @property
    def database_url(self) -> str:
        return f'mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'


settings = Settings()
