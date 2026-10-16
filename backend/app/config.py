"""
config.py — Configuración centralizada mediante pydantic-settings.

Lee las variables de entorno desde el archivo .env en la raíz del proyecto
y las expone como atributos tipados a través de la instancia global `settings`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Clase de configuración global del backend.
    Todas las variables se leen desde el entorno o desde un archivo .env.
    """

    # --- Base de Datos ---
    database_url: str = "mysql+pymysql://banca_user:banca_password_2024@localhost:3306/banca_db"

    # --- API Key de Mistral ---
    mistral_api_key: str

    # --- URL del microservicio Drools ---
    drools_url: str = "http://localhost:8080/api/evaluate"

    # --- Modelo de Mistral a utilizar ---
    mistral_model: str = "ministral-8b-latest"

    # --- Timeout para llamadas HTTP a Drools (segundos) ---
    drools_timeout: int = 30

    # --- Ruta al archivo de datos mock del BdE (CIRBE/ASNEF) ---
    bde_json_path: str = "bde.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Devuelve la instancia cacheada de Settings.
    El decorador lru_cache garantiza que se instancia una sola vez
    durante todo el ciclo de vida de la aplicación.
    """
    return Settings()


# Instancia global para importación directa en otros módulos
settings: Settings = get_settings()
