from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_provider_registry  # noqa: E402
from app.db.base import Base, import_models  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.integrations.fakes import (  # noqa: E402
    FakeEmbeddingProvider,
    FakeLlmProvider,
    FakeOcrProvider,
    FakeQueryRewriteProvider,
    FakeSimilarityProvider,
)
from app.main import app  # noqa: E402


class FakeProviderRegistryForTests:
    def get_llm_provider(self) -> FakeLlmProvider:
        return FakeLlmProvider()

    def get_ocr_provider(self) -> FakeOcrProvider:
        return FakeOcrProvider()

    def get_embedding_provider(self) -> FakeEmbeddingProvider:
        return FakeEmbeddingProvider()

    def get_similarity_provider(self) -> FakeSimilarityProvider:
        return FakeSimilarityProvider()

    def get_query_rewrite_provider(self) -> FakeQueryRewriteProvider:
        return FakeQueryRewriteProvider()


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session]:
    import_models()
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient]:
    def override_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_provider_registry] = lambda: FakeProviderRegistryForTests()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": "learner@example.com", "password": "StrongPass123", "display_name": "Learner"},
    )
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
