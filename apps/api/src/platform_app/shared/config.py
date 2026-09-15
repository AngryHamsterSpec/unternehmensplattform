"""Explizite Laufzeitkonfiguration; Demo-Ausnahmen gelten ausschließlich lokal."""

from decimal import Decimal, InvalidOperation
from functools import lru_cache
from urllib.parse import urlsplit
from uuid import UUID

from cryptography.fernet import Fernet
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://platform_app@postgres/platform", repr=False
    )
    auth_database_url: str = Field(
        default="postgresql+psycopg://platform_auth@postgres/platform", repr=False
    )
    migration_database_url: str = Field(
        default="postgresql+psycopg://platform_migrator@postgres/platform", repr=False
    )
    public_origin: str = "http://localhost:8080"
    http_demo_mode: bool = True
    oidc_issuer: str = "http://localhost:8080/identity/realms/platform"
    oidc_internal_base_url: str = "http://keycloak:8080/identity"
    oidc_client_id: str = "platform"
    oidc_client_secret: str = Field(min_length=24, repr=False)
    session_secret: str = Field(min_length=32, repr=False)
    oidc_encryption_key: str = Field(min_length=40, repr=False)
    openai_enabled: bool = False
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = ""
    openai_price_version: str = ""
    openai_input_per_million: str = ""
    openai_output_per_million: str = ""
    openai_daily_budget: str = "1.00"
    openai_organization_ids: str = ""
    request_limit_per_minute: int = Field(default=180, ge=10, le=10000)
    dataset_limit_per_organization: int = Field(default=1000, ge=1, le=100000)

    @model_validator(mode="after")
    def secure_configuration(self) -> "AppSettings":
        origin = urlsplit(self.public_origin)
        if (
            not origin.hostname
            or origin.path
            or origin.query
            or origin.fragment
            or origin.username is not None
            or origin.password is not None
        ):
            raise ValueError("PUBLIC_ORIGIN muss ein Ursprung ohne Pfad sein.")
        if self.http_demo_mode:
            if self.environment not in {"development", "test", "demo"}:
                raise ValueError("HTTP-Demo ist in diesem Betriebsmodus verboten.")
            if origin.scheme != "http" or origin.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("HTTP-Demo benötigt einen Loopback-Ursprung.")
        elif origin.scheme != "https":
            raise ValueError("Außerhalb der lokalen Demo ist HTTPS erforderlich.")
        if self.openai_enabled and not all(
            [
                self.openai_api_key,
                self.openai_model,
                self.openai_price_version,
                self.openai_input_per_million,
                self.openai_output_per_million,
                self.openai_organization_ids,
            ]
        ):
            raise ValueError(
                "Live-KI benötigt Modell, Preisstand, Budget und Organisationsfreigabe."
            )
        try:
            Fernet(self.oidc_encryption_key.encode())
        except (ValueError, TypeError):
            raise ValueError(
                "OIDC_ENCRYPTION_KEY muss ein gültiger Fernet-Schlüssel sein."
            ) from None
        issuer = urlsplit(self.oidc_issuer)
        if (
            issuer.username is not None
            or issuer.password is not None
            or issuer.query
            or issuer.fragment
            or not issuer.hostname
            or issuer.scheme not in {"http", "https"}
        ):
            raise ValueError("Ungültiger OIDC-Aussteller.")
        if not self.http_demo_mode and issuer.scheme != "https":
            raise ValueError("OIDC benötigt außerhalb der Demo HTTPS.")
        if (
            self.http_demo_mode
            and issuer.scheme == "http"
            and issuer.hostname not in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError("HTTP-OIDC ist nur für die lokale Demo erlaubt.")
        transport = urlsplit(self.oidc_internal_base_url)
        if (
            not transport.hostname
            or transport.scheme not in {"http", "https"}
            or transport.username is not None
            or transport.password is not None
            or transport.query
            or transport.fragment
        ):
            raise ValueError("Ungültiger interner OIDC-Endpunkt.")
        if not self.http_demo_mode and transport.scheme != "https":
            raise ValueError("Der interne OIDC-Transport benötigt außerhalb der Demo HTTPS.")
        if self.openai_enabled:
            try:
                amounts = [
                    Decimal(self.openai_input_per_million),
                    Decimal(self.openai_output_per_million),
                    Decimal(self.openai_daily_budget),
                ]
                if any(not v.is_finite() or v <= 0 for v in amounts):
                    raise ValueError("Preis und Budget müssen endlich und positiv sein.")
                for value in self.openai_organization_ids.split(","):
                    UUID(value.strip())
            except (ValueError, InvalidOperation):
                raise ValueError(
                    "Ungültige KI-Preise, Tagesbudget oder Organisationsfreigabe."
                ) from None
        return self


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
