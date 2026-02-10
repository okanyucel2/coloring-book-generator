"""Tests for Etsy batch publishing endpoint.

Covers:
  - Batch publish multiple workbooks in one request
  - Per-item error handling (partial failures)
  - Skip logic: not found, not ready, already published, no PDF
  - Rate limit stops entire batch
  - Empty/oversized batch validation
"""

import os
from unittest.mock import patch

import coloring_book.api.etsy_routes as etsy_routes_module
import pytest
from coloring_book.api import models
from coloring_book.api import workbook_routes as wr_module
from coloring_book.api.app import DEFAULT_USER_ID, app
from coloring_book.api.workbook_routes import _generation_tasks, _pdfs
from coloring_book.etsy.client import (
    EtsyListing,
    EtsyRateLimitError,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def db_session(monkeypatch):
    """Create fresh in-memory SQLite databases (sync + async) for each test."""
    # Sync engine for direct DB manipulation in tests
    sync_engine = create_engine(
        "sqlite:///file:batch_test?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Async engine pointing to the same shared in-memory DB
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///file:batch_test?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=sync_engine)
    SyncSession = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    AsyncTestSession = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    # Create default system user
    session = SyncSession()
    session.add(models.User(
        id=DEFAULT_USER_ID,
        email="system@localhost",
        name="System",
        provider="system",
    ))
    session.commit()
    session.close()

    # Override get_db with async session
    async def override_get_db():
        async with AsyncTestSession() as db:
            yield db

    app.dependency_overrides[models.get_db] = override_get_db
    monkeypatch.setattr(wr_module, "SessionLocal", SyncSession)

    _pdfs.clear()
    _generation_tasks.clear()
    etsy_routes_module._pending_states.clear()

    yield SyncSession

    app.dependency_overrides.clear()
    _pdfs.clear()
    _generation_tasks.clear()
    etsy_routes_module._pending_states.clear()
    models.Base.metadata.drop_all(bind=sync_engine)


@pytest.fixture
def client():
    return TestClient(app)


def _connect_etsy(client):
    """Helper: complete Etsy OAuth flow so endpoints have tokens."""
    from coloring_book.etsy.client import EtsyClient, TokenResponse

    async def mock_exchange(self, code):
        self.tokens = TokenResponse(
            access_token="test_access", refresh_token="test_refresh",
            token_type="Bearer", expires_in=3600,
        )
        return self.tokens

    async def mock_get_me(self):
        return {"user_id": 111, "shop_id": 99999, "shop_name": "BatchTestShop"}

    with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
        auth_resp = client.get("/api/v1/etsy/auth-url")
        state = auth_resp.json()["state"]
        with patch.object(EtsyClient, "exchange_code", mock_exchange), \
             patch.object(EtsyClient, "get_me", mock_get_me):
            client.get("/api/v1/etsy/callback", params={"code": "c", "state": state})


def _create_ready_workbook(db_session, theme="animals", title="Test WB", status="ready"):
    """Create a workbook directly in DB, set to ready, and add fake PDF."""
    import uuid
    wb_id = str(uuid.uuid4())

    session = db_session()
    wb = models.WorkbookModel(
        id=wb_id,
        theme=theme,
        title=title,
        items_json=["cat", "dog"],
        activity_mix_json={"trace_and_color": 2},
        page_count=10,
        age_min=3,
        age_max=8,
        page_size="letter",
        status=status,
    )
    session.add(wb)
    session.commit()
    session.close()

    if status == "ready":
        _pdfs[wb_id] = b"%PDF-1.4 fake content"
    return wb_id


def _mock_create_listing():
    """Mock EtsyListingService.create_listing to return a fake listing."""
    call_count = {"n": 0}

    async def mock_create(self, config, pdf_bytes, price_override=None, **kw):
        call_count["n"] += 1
        return EtsyListing(
            listing_id=100000 + call_count["n"],
            title=config.title,
            description="test",
            price=price_override or 4.99,
            state="draft",
        )

    return mock_create


class TestBatchPublishBasic:
    def test_batch_publish_multiple_workbooks(self, client, db_session):
        _connect_etsy(client)

        wb1 = _create_ready_workbook(db_session, title="WB1")
        wb2 = _create_ready_workbook(db_session, title="WB2")
        wb3 = _create_ready_workbook(db_session, title="WB3")

        from coloring_book.etsy.listing import EtsyListingService
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}), \
             patch.object(EtsyListingService, "create_listing", _mock_create_listing()):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [wb1, wb2, wb3],
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["succeeded"] == 3
        assert data["failed"] == 0
        assert data["skipped"] == 0
        assert all(r["status"] == "success" for r in data["results"])
        assert all(r["listing_id"] is not None for r in data["results"])

    def test_batch_publish_empty_list(self, client):
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [],
            })
        assert resp.status_code == 400

    def test_batch_publish_not_authenticated(self, client):
        # Disconnect first to ensure no tokens
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            client.post("/api/v1/etsy/disconnect")
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": ["fake-id"],
            })
        assert resp.status_code == 401


class TestBatchPublishSkipLogic:
    def test_skips_not_found_workbook(self, client, db_session):
        _connect_etsy(client)
        wb1 = _create_ready_workbook(db_session, title="Good")

        from coloring_book.etsy.listing import EtsyListingService
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}), \
             patch.object(EtsyListingService, "create_listing", _mock_create_listing()):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": ["nonexistent-id", wb1],
            })

        data = resp.json()
        assert data["total"] == 2
        assert data["skipped"] == 1
        assert data["succeeded"] == 1
        assert data["results"][0]["status"] == "skipped"
        assert data["results"][0]["error"] == "Workbook not found"
        assert data["results"][1]["status"] == "success"

    def test_skips_not_ready_workbook(self, client, db_session):
        _connect_etsy(client)
        not_ready_id = _create_ready_workbook(db_session, title="Not Ready", status="generating")
        wb_ready = _create_ready_workbook(db_session, title="Ready")

        from coloring_book.etsy.listing import EtsyListingService
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}), \
             patch.object(EtsyListingService, "create_listing", _mock_create_listing()):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [not_ready_id, wb_ready],
            })

        data = resp.json()
        assert data["skipped"] == 1
        assert data["succeeded"] == 1
        assert "not ready" in data["results"][0]["error"].lower()

    def test_skips_already_published(self, client, db_session):
        _connect_etsy(client)
        wb1 = _create_ready_workbook(db_session, title="Already Published")

        # Mark as already published
        session = db_session()
        wb = session.query(models.WorkbookModel).filter(
            models.WorkbookModel.id == wb1
        ).first()
        wb.etsy_listing_id = "99999"
        session.commit()
        session.close()

        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [wb1],
            })

        data = resp.json()
        assert data["skipped"] == 1
        assert "Already published" in data["results"][0]["error"]

    def test_recompiles_when_no_cached_pdf(self, client, db_session):
        """Ready workbooks without cached PDF are re-compiled at 300 DPI for Etsy."""
        _connect_etsy(client)
        wb1 = _create_ready_workbook(db_session, title="Recompile Me")
        # Remove the cached home PDF — should still publish via re-compile
        _pdfs.pop(wb1, None)

        from coloring_book.etsy.listing import EtsyListingService
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}), \
             patch.object(EtsyListingService, "create_listing", _mock_create_listing()):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [wb1],
            })

        data = resp.json()
        assert data["succeeded"] == 1
        assert data["results"][0]["status"] == "success"


class TestBatchPublishErrorHandling:
    def test_partial_failure_continues(self, client, db_session):
        _connect_etsy(client)
        wb1 = _create_ready_workbook(db_session, title="WB1")
        wb2 = _create_ready_workbook(db_session, title="WB2")
        wb3 = _create_ready_workbook(db_session, title="WB3")

        call_count = {"n": 0}

        async def mock_create_with_failure(self, config, pdf_bytes, **kw):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("Etsy API intermittent error")
            return EtsyListing(
                listing_id=200000 + call_count["n"],
                title=config.title, description="ok", price=4.99, state="draft",
            )

        from coloring_book.etsy.listing import EtsyListingService
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}), \
             patch.object(EtsyListingService, "create_listing", mock_create_with_failure):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [wb1, wb2, wb3],
            })

        data = resp.json()
        assert data["succeeded"] == 2
        assert data["failed"] == 1
        assert data["results"][0]["status"] == "success"
        assert data["results"][1]["status"] == "error"
        assert data["results"][2]["status"] == "success"

    def test_rate_limit_stops_batch(self, client, db_session):
        _connect_etsy(client)
        wb1 = _create_ready_workbook(db_session, title="WB1")
        wb2 = _create_ready_workbook(db_session, title="WB2")
        wb3 = _create_ready_workbook(db_session, title="WB3")

        async def mock_rate_limit(self, config, pdf_bytes, **kw):
            raise EtsyRateLimitError(retry_after=30)

        from coloring_book.etsy.listing import EtsyListingService
        with patch.dict(os.environ, {"ETSY_API_KEY": "key", "ETSY_API_SECRET": "secret"}), \
             patch.object(EtsyListingService, "create_listing", mock_rate_limit):
            resp = client.post("/api/v1/etsy/workbooks/batch-publish", json={
                "workbook_ids": [wb1, wb2, wb3],
            })

        data = resp.json()
        assert data["total"] == 3
        assert data["failed"] == 1  # first item rate limited
        assert data["skipped"] == 2  # remaining skipped
        assert "rate limit" in data["results"][0]["error"].lower()
        assert data["results"][1]["status"] == "skipped"
        assert data["results"][2]["status"] == "skipped"
