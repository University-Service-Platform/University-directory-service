import pytest

from app.config import (
    AUTH_MODE_IDENTITY_HS256,
    AUTH_MODE_JWKS,
    DEFAULT_DATABASE_URL,
    ConfigurationError,
    load_settings,
)


def test_defaults_when_environment_is_empty():
    settings = load_settings({})

    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.identity_service_base_url is None
    assert settings.identity_timeout_connect == 3.0
    assert settings.identity_timeout_read == 5.0
    assert settings.auth_mode == AUTH_MODE_IDENTITY_HS256
    assert settings.jwt_secret_key is None
    assert settings.resolved_jwks_url is None


def test_values_are_read_from_environment():
    settings = load_settings({
        "DATABASE_URL": "sqlite:///./other.db",
        "IDENTITY_SERVICE_BASE_URL": "http://identity.test/",
        "IDENTITY_TIMEOUT_CONNECT": "1.5",
        "IDENTITY_TIMEOUT_READ": "2",
        "AUTH_MODE": "JWKS",
        "JWT_ISSUER": "issuer-x",
        "JWT_AUDIENCE": "audience-y",
    })

    assert settings.database_url == "sqlite:///./other.db"
    assert settings.identity_service_base_url == "http://identity.test"
    assert settings.identity_timeout_connect == 1.5
    assert settings.identity_timeout_read == 2.0
    assert settings.auth_mode == AUTH_MODE_JWKS
    assert settings.jwt_issuer == "issuer-x"
    assert settings.jwt_audience == "audience-y"
    assert settings.resolved_jwks_url == "http://identity.test/.well-known/jwks.json"


def test_explicit_jwks_url_takes_precedence():
    settings = load_settings({
        "IDENTITY_SERVICE_BASE_URL": "http://identity.test",
        "JWKS_URL": "http://keys.test/jwks.json",
    })
    assert settings.resolved_jwks_url == "http://keys.test/jwks.json"


def test_unknown_auth_mode_rejected():
    with pytest.raises(ConfigurationError):
        load_settings({"AUTH_MODE": "none"})


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_timeout_rejected(value):
    with pytest.raises(ConfigurationError):
        load_settings({"IDENTITY_TIMEOUT_READ": value})
