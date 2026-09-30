import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.auth import get_token_verifier
from app.database import Base, get_db
from app.integrations.identity_client import get_identity_client
from app.main import app
from tests.auth_support import ADMIN_TOKEN, bearer, make_test_verifier
from tests.fakes import FakeIdentityClient

# SQLite by default; set TEST_DATABASE_URL (e.g. a PostgreSQL URL) to run the suite against another database.
SQLALCHEMY_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or "sqlite:///./test_directory.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def identity_client():
    """Fake Identity Service; every user is ACTIVE unless a test configures otherwise."""
    fake = FakeIdentityClient()
    fake.roles["usr-admin-001"] = ("ADMIN",)  # matches the synthetic ADMIN_TOKEN subject
    return fake

@pytest.fixture(scope="function")
def anon_client(db_session, identity_client):
    """Client with test overrides but no Authorization header."""
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass

    test_verifier = make_test_verifier()
    app.dependency_overrides[get_db] = _get_test_db
    app.dependency_overrides[get_token_verifier] = lambda: test_verifier
    app.dependency_overrides[get_identity_client] = lambda: identity_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client(anon_client):
    """Client authenticated as a synthetic ADMIN user (locally signed RS256 token)."""
    anon_client.headers.update(bearer(ADMIN_TOKEN))
    return anon_client
