"""
Comprehensive API endpoint tests for Coloring Book Generator.

TDD RED PHASE: All tests target the real FastAPI app via httpx AsyncClient + ASGITransport.
Every test should FAIL against the current 501-stub implementation, validating that our
test suite genuinely enforces the contract before production code is written.

The health endpoint is the only one currently implemented (returns 200).
All other endpoints return 501, so the vast majority of tests will fail.

Endpoint groups:
  1. Health Check (GET /api/health)
  2. Prompt Library CRUD (GET/POST/PUT/DELETE /api/v1/prompts/library)
  3. Variation History (GET/PATCH/DELETE /api/v1/variations)
  4. Edge Cases (CORS, unicode, concurrency, idempotency)
"""

import asyncio
import uuid
import pytest
import httpx
from datetime import datetime, timezone
from httpx import ASGITransport
from src.coloring_book.api.app import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """Create async test client backed by in-memory SQLite.

    Each test gets a completely fresh database so tests remain independent.
    The FastAPI dependency for get_db is overridden to use the test engine.
    """
    from src.coloring_book.api import models
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[models.get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # Attach session factory so helpers can seed the DB directly
        c._test_session_factory = TestSession
        yield c

    app.dependency_overrides.clear()
    models.Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_prompt(client: httpx.AsyncClient, **overrides) -> httpx.Response:
    """Convenience helper to POST a valid prompt and return the httpx Response."""
    payload = {
        "name": overrides.get("name", "Test Prompt"),
        "promptText": overrides.get("promptText", "Draw a cute {{animal}} in {{style}} style"),
        "tags": overrides.get("tags", ["animal", "cute"]),
        "category": overrides.get("category", "animals"),
        "isPublic": overrides.get("isPublic", True),
    }
    resp = await client.post("/api/v1/prompts/library", json=payload)
    return resp


def _seed_variation_in_db(client: httpx.AsyncClient, **overrides) -> str:
    """Insert a Variation row directly into the test DB and return its ID.

    This bypasses the API entirely so variation PATCH/DELETE tests do not
    depend on a POST endpoint existing.
    """
    from src.coloring_book.api.models import Variation

    var_id = overrides.get("id", str(uuid.uuid4()))
    session = client._test_session_factory()
    try:
        variation = Variation(
            id=var_id,
            prompt=overrides.get("prompt", "Draw a cat"),
            model=overrides.get("model", "claude"),
            image_url=overrides.get("image_url", ""),
            rating=overrides.get("rating", 3),
            seed=overrides.get("seed", 0),
            notes=overrides.get("notes", ""),
            parameters=overrides.get("parameters", {}),
            generated_at=overrides.get("generated_at", datetime.now(timezone.utc)),
        )
        session.add(variation)
        session.commit()
    finally:
        session.close()
    return var_id


# ===========================================================================
# 1. HEALTH CHECK
# ===========================================================================

class TestHealthCheck:
    """GET /api/health must return 200 with status ok."""

    async def test_health_returns_200_with_status_ok(self, client):
        """Health endpoint returns HTTP 200 and body {"status": "ok"}."""
        resp = await client.get("/api/health")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "ok", f"Expected status 'ok', got {body.get('status')}"

    async def test_health_response_content_type_is_json(self, client):
        """Health endpoint must return application/json content type."""
        resp = await client.get("/api/health")

        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Expected application/json content-type, got '{content_type}'"
        )


# ===========================================================================
# 2. PROMPT LIBRARY CRUD
# ===========================================================================

class TestPromptLibraryList:
    """GET /api/v1/prompts/library"""

    async def test_list_returns_200_with_data_key(self, client):
        """GET returns 200 and response body contains a 'data' key."""
        resp = await client.get("/api/v1/prompts/library")

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body, f"Response missing 'data' key: {body}"

    async def test_list_returns_empty_list_when_no_prompts(self, client):
        """GET on a fresh DB returns an empty list inside 'data'."""
        resp = await client.get("/api/v1/prompts/library")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == [], f"Expected empty list, got {body['data']}"

    async def test_list_returns_prompts_after_creation(self, client):
        """After creating two prompts, GET returns both of them."""
        await _create_prompt(client, name="Prompt A")
        await _create_prompt(client, name="Prompt B")

        resp = await client.get("/api/v1/prompts/library")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert len(data) == 2, f"Expected 2 prompts, got {len(data)}"

        names = {p["name"] for p in data}
        assert names == {"Prompt A", "Prompt B"}, f"Unexpected names: {names}"


class TestPromptLibraryCreate:
    """POST /api/v1/prompts/library"""

    async def test_create_returns_201_with_full_prompt(self, client):
        """POST with valid payload returns 201 and the created prompt object."""
        resp = await _create_prompt(client, name="My Prompt", promptText="Draw {{animal}}")

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"

        body = resp.json()
        assert "id" in body, "Response missing 'id'"
        assert body["name"] == "My Prompt"
        assert body["promptText"] == "Draw {{animal}}"
        assert "createdAt" in body, "Response missing 'createdAt' timestamp"

    async def test_create_validates_missing_name(self, client):
        """POST without 'name' returns 422 (Unprocessable Entity)."""
        payload = {"promptText": "Draw something"}
        resp = await client.post("/api/v1/prompts/library", json=payload)

        assert resp.status_code == 422, f"Expected 422 for missing name, got {resp.status_code}"

    async def test_create_validates_missing_prompt_text(self, client):
        """POST without 'promptText' returns 422."""
        payload = {"name": "Valid Name"}
        resp = await client.post("/api/v1/prompts/library", json=payload)

        assert resp.status_code == 422, f"Expected 422 for missing promptText, got {resp.status_code}"

    async def test_create_validates_prompt_text_max_length(self, client):
        """POST with promptText exceeding 2000 chars returns 422."""
        long_text = "x" * 2001
        resp = await _create_prompt(client, promptText=long_text)

        assert resp.status_code == 422, (
            f"Expected 422 for promptText > 2000 chars, got {resp.status_code}"
        )

    async def test_create_validates_empty_name(self, client):
        """POST with an empty string name returns 422."""
        resp = await _create_prompt(client, name="")

        assert resp.status_code == 422, f"Expected 422 for empty name, got {resp.status_code}"

    async def test_create_stores_tags_as_array(self, client):
        """Tags submitted as a list are persisted and returned as a list."""
        tags = ["forest", "nature", "animal"]
        resp = await _create_prompt(client, tags=tags)

        assert resp.status_code == 201
        body = resp.json()
        assert body["tags"] == tags, f"Expected tags {tags}, got {body.get('tags')}"

    async def test_create_stores_category_and_is_public(self, client):
        """Category and isPublic fields are stored and returned correctly."""
        resp = await _create_prompt(
            client,
            category="fantasy",
            isPublic=False,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["category"] == "fantasy", (
            f"Expected category 'fantasy', got {body.get('category')}"
        )
        assert body["isPublic"] is False, (
            f"Expected isPublic=False, got {body.get('isPublic')}"
        )

    async def test_create_generates_unique_ids(self, client):
        """Two separately created prompts must have different IDs."""
        resp1 = await _create_prompt(client, name="First")
        resp2 = await _create_prompt(client, name="Second")

        assert resp1.status_code == 201
        assert resp2.status_code == 201

        id1 = resp1.json()["id"]
        id2 = resp2.json()["id"]
        assert id1 != id2, f"IDs should be unique but both are {id1}"

    async def test_create_sets_created_at_timestamp(self, client):
        """createdAt timestamp must be a non-empty ISO-format string."""
        resp = await _create_prompt(client)

        assert resp.status_code == 201
        created_at = resp.json()["createdAt"]
        assert isinstance(created_at, str) and len(created_at) > 0, (
            f"Expected non-empty createdAt string, got {created_at!r}"
        )


class TestPromptLibraryUpdate:
    """PUT /api/v1/prompts/library/{id}"""

    async def test_update_returns_200_with_updated_prompt(self, client):
        """Full update returns 200 and the modified prompt."""
        create_resp = await _create_prompt(client, name="Original")
        prompt_id = create_resp.json()["id"]

        update_payload = {"name": "Updated Name", "promptText": "New text here"}
        resp = await client.put(
            f"/api/v1/prompts/library/{prompt_id}", json=update_payload
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        body = resp.json()
        assert body["name"] == "Updated Name"
        assert body["promptText"] == "New text here"

    async def test_update_partial_fields(self, client):
        """Partial update (only name) leaves other fields unchanged."""
        create_resp = await _create_prompt(
            client,
            name="Original",
            promptText="Keep this text",
            category="nature",
        )
        prompt_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/prompts/library/{prompt_id}",
            json={"name": "New Name Only"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name Only"
        assert body["promptText"] == "Keep this text", (
            "promptText should not change on partial update"
        )
        assert body["category"] == "nature", (
            "category should not change on partial update"
        )

    async def test_update_nonexistent_prompt_returns_404(self, client):
        """PUT to a non-existent ID returns 404."""
        resp = await client.put(
            "/api/v1/prompts/library/nonexistent-id-999",
            json={"name": "Ghost"},
        )

        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    async def test_update_sets_updated_at_timestamp(self, client):
        """After update, updatedAt should be set and differ from createdAt."""
        create_resp = await _create_prompt(client, name="Timestamped")
        prompt_id = create_resp.json()["id"]
        created_at = create_resp.json()["createdAt"]

        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.05)

        resp = await client.put(
            f"/api/v1/prompts/library/{prompt_id}",
            json={"name": "Renamed"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "updatedAt" in body, "Response missing 'updatedAt' after update"
        assert body["updatedAt"] is not None, "updatedAt should not be None after update"
        # updatedAt should be different from (and later than) createdAt
        assert body["updatedAt"] != created_at, (
            f"updatedAt ({body['updatedAt']}) should differ from createdAt ({created_at})"
        )


class TestPromptLibraryDelete:
    """DELETE /api/v1/prompts/library/{id}"""

    async def test_delete_returns_200_on_success(self, client):
        """DELETE an existing prompt returns 200."""
        create_resp = await _create_prompt(client, name="To Delete")
        prompt_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/prompts/library/{prompt_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    async def test_delete_nonexistent_returns_404(self, client):
        """DELETE a non-existent prompt returns 404."""
        resp = await client.delete("/api/v1/prompts/library/does-not-exist-42")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    async def test_deleted_prompt_no_longer_in_list(self, client):
        """After deletion, the prompt must not appear in GET list."""
        create_resp = await _create_prompt(client, name="Ephemeral")
        prompt_id = create_resp.json()["id"]

        # Delete it
        del_resp = await client.delete(f"/api/v1/prompts/library/{prompt_id}")
        assert del_resp.status_code == 200

        # Verify it's gone
        list_resp = await client.get("/api/v1/prompts/library")
        data = list_resp.json()["data"]
        remaining_ids = [p["id"] for p in data]
        assert prompt_id not in remaining_ids, (
            f"Deleted prompt {prompt_id} still appears in list: {remaining_ids}"
        )


# ===========================================================================
# 3. VARIATION HISTORY
# ===========================================================================

class TestVariationHistoryList:
    """GET /api/v1/variations/history"""

    async def test_list_returns_200_with_data_key(self, client):
        """GET returns 200 with a 'data' array."""
        resp = await client.get("/api/v1/variations/history")

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body, f"Response missing 'data' key: {body}"

    async def test_list_returns_empty_when_no_variations(self, client):
        """Fresh DB has no variations -- data should be an empty list."""
        resp = await client.get("/api/v1/variations/history")

        assert resp.status_code == 200
        assert resp.json()["data"] == [], (
            f"Expected empty list, got {resp.json()['data']}"
        )

    async def test_list_returns_seeded_variations(self, client):
        """After seeding variations in DB, GET returns them."""
        _seed_variation_in_db(client, prompt="Draw a cat")
        _seed_variation_in_db(client, prompt="Draw a dog")

        resp = await client.get("/api/v1/variations/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2, f"Expected 2 variations, got {len(data)}"


class TestVariationPatch:
    """PATCH /api/v1/variations/{id}"""

    async def test_patch_updates_rating(self, client):
        """PATCH with a valid rating (1-5) updates the variation."""
        var_id = _seed_variation_in_db(client, rating=3)

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"rating": 5},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        body = resp.json()
        assert body["rating"] == 5, f"Expected rating 5, got {body.get('rating')}"

    async def test_patch_updates_notes(self, client):
        """PATCH with notes updates the variation's notes field."""
        var_id = _seed_variation_in_db(client, notes="")

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"notes": "This one looks great!"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["notes"] == "This one looks great!", (
            f"Expected updated notes, got {body.get('notes')}"
        )

    async def test_patch_nonexistent_returns_404(self, client):
        """PATCH a non-existent variation returns 404."""
        resp = await client.patch(
            "/api/v1/variations/nonexistent-var-id",
            json={"rating": 3},
        )

        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    async def test_patch_validates_rating_too_low(self, client):
        """PATCH with rating 0 (below minimum 1) returns 422."""
        var_id = _seed_variation_in_db(client, rating=3)

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"rating": 0},
        )

        assert resp.status_code == 422, (
            f"Expected 422 for rating=0, got {resp.status_code}"
        )

    async def test_patch_validates_rating_too_high(self, client):
        """PATCH with rating 6 (above maximum 5) returns 422."""
        var_id = _seed_variation_in_db(client, rating=3)

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"rating": 6},
        )

        assert resp.status_code == 422, (
            f"Expected 422 for rating=6, got {resp.status_code}"
        )

    async def test_patch_rating_boundary_min(self, client):
        """PATCH with rating=1 (minimum valid) succeeds."""
        var_id = _seed_variation_in_db(client, rating=3)

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"rating": 1},
        )

        assert resp.status_code == 200
        assert resp.json()["rating"] == 1

    async def test_patch_rating_boundary_max(self, client):
        """PATCH with rating=5 (maximum valid) succeeds."""
        var_id = _seed_variation_in_db(client, rating=3)

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"rating": 5},
        )

        assert resp.status_code == 200
        assert resp.json()["rating"] == 5

    async def test_patch_updates_both_rating_and_notes(self, client):
        """PATCH with both rating and notes updates both fields simultaneously."""
        var_id = _seed_variation_in_db(client, rating=1, notes="old note")

        resp = await client.patch(
            f"/api/v1/variations/{var_id}",
            json={"rating": 4, "notes": "new note"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["rating"] == 4, f"Expected rating 4, got {body.get('rating')}"
        assert body["notes"] == "new note", f"Expected 'new note', got {body.get('notes')}"


class TestVariationDelete:
    """DELETE /api/v1/variations/{id}"""

    async def test_delete_returns_200_on_success(self, client):
        """DELETE an existing variation returns 200."""
        var_id = _seed_variation_in_db(client)

        resp = await client.delete(f"/api/v1/variations/{var_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    async def test_delete_nonexistent_returns_404(self, client):
        """DELETE a non-existent variation returns 404."""
        resp = await client.delete("/api/v1/variations/ghost-variation-99")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    async def test_deleted_variation_not_in_history(self, client):
        """After deleting a variation, it no longer appears in history list."""
        var_id = _seed_variation_in_db(client)

        del_resp = await client.delete(f"/api/v1/variations/{var_id}")
        assert del_resp.status_code == 200

        list_resp = await client.get("/api/v1/variations/history")
        assert list_resp.status_code == 200
        data = list_resp.json()["data"]
        remaining_ids = [v["id"] for v in data]
        assert var_id not in remaining_ids, (
            f"Deleted variation {var_id} still in history: {remaining_ids}"
        )


class TestVariationHistoryClear:
    """DELETE /api/v1/variations/history (clear all)"""

    async def test_clear_all_returns_200(self, client):
        """DELETE /api/v1/variations/history returns 200 with confirmation."""
        _seed_variation_in_db(client, prompt="Cat")
        _seed_variation_in_db(client, prompt="Dog")

        resp = await client.delete("/api/v1/variations/history")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        body = resp.json()
        # Response should contain confirmation message or deleted count
        assert any(
            key in body for key in ("message", "deleted", "count")
        ), f"Expected confirmation in response body, got {body}"

    async def test_clear_all_empties_history(self, client):
        """After clearing, GET /api/v1/variations/history returns empty list."""
        _seed_variation_in_db(client, prompt="Cat")
        _seed_variation_in_db(client, prompt="Dog")
        _seed_variation_in_db(client, prompt="Bird")

        # Clear all
        clear_resp = await client.delete("/api/v1/variations/history")
        assert clear_resp.status_code == 200

        # Verify emptied
        list_resp = await client.get("/api/v1/variations/history")
        assert list_resp.status_code == 200
        data = list_resp.json()["data"]
        assert data == [], f"Expected empty list after clear, got {data}"

    async def test_clear_on_empty_still_returns_200(self, client):
        """Clearing an already-empty history still returns 200 (idempotent)."""
        resp = await client.delete("/api/v1/variations/history")
        assert resp.status_code == 200


# ===========================================================================
# 4. EDGE CASES
# ===========================================================================

class TestEdgeCases:
    """Cross-cutting concerns: CORS, encoding, concurrency, idempotency."""

    async def test_cors_headers_present(self, client):
        """Response includes CORS-related headers (Access-Control-Allow-Origin)."""
        # CORSMiddleware only sends CORS headers when Origin header is present
        resp = await client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"},
        )

        # FastAPI CORSMiddleware sets this header when Origin is in allowed origins
        allow_origin = resp.headers.get("access-control-allow-origin")
        assert allow_origin is not None, (
            "Missing 'access-control-allow-origin' header. "
            f"Headers present: {dict(resp.headers)}"
        )

    async def test_large_payload_at_max_length(self, client):
        """Prompt with exactly 2000 characters (max allowed) succeeds."""
        max_text = "A" * 2000
        resp = await _create_prompt(client, name="Max Length", promptText=max_text)

        assert resp.status_code == 201, (
            f"Expected 201 for 2000-char prompt, got {resp.status_code}"
        )
        body = resp.json()
        assert len(body["promptText"]) == 2000, (
            f"Expected 2000 chars stored, got {len(body['promptText'])}"
        )

    async def test_special_characters_unicode(self, client):
        """Prompt text with unicode characters is stored and returned correctly."""
        unicode_text = "Bir kedi \u00e7iz - avec des fleurs - mit Bl\u00fcmen"
        resp = await _create_prompt(
            client,
            name="Unicode Test",
            promptText=unicode_text,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["promptText"] == unicode_text, (
            f"Unicode text mismatch: expected {unicode_text!r}, got {body['promptText']!r}"
        )

    async def test_special_characters_emoji(self, client):
        """Prompt text containing emoji is stored and returned correctly."""
        emoji_text = "Draw a happy \U0001f431 cat with \u2b50 stars around it"
        resp = await _create_prompt(
            client,
            name="Emoji Prompt",
            promptText=emoji_text,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["promptText"] == emoji_text, (
            f"Emoji text mismatch: expected {emoji_text!r}, got {body['promptText']!r}"
        )

    async def test_multiple_rapid_creates_no_race_condition(self, client):
        """Creating many prompts concurrently should not cause duplicates or errors."""
        num_concurrent = 10

        async def create_one(i: int):
            return await _create_prompt(client, name=f"Concurrent-{i}")

        responses = await asyncio.gather(
            *[create_one(i) for i in range(num_concurrent)]
        )

        # All should succeed
        for i, resp in enumerate(responses):
            assert resp.status_code == 201, (
                f"Concurrent create {i} failed with {resp.status_code}: {resp.text}"
            )

        # All IDs should be unique
        ids = [r.json()["id"] for r in responses]
        assert len(ids) == len(set(ids)), (
            f"Expected {num_concurrent} unique IDs, got duplicates: {ids}"
        )

        # Final list should contain all of them
        list_resp = await client.get("/api/v1/prompts/library")
        assert list_resp.status_code == 200
        data = list_resp.json()["data"]
        assert len(data) == num_concurrent, (
            f"Expected {num_concurrent} prompts in list, got {len(data)}"
        )

    async def test_delete_already_deleted_prompt_returns_404(self, client):
        """Deleting a prompt that was already deleted returns 404 (idempotent safety)."""
        create_resp = await _create_prompt(client, name="Double Delete")
        prompt_id = create_resp.json()["id"]

        # First delete succeeds
        first_del = await client.delete(f"/api/v1/prompts/library/{prompt_id}")
        assert first_del.status_code == 200

        # Second delete returns 404
        second_del = await client.delete(f"/api/v1/prompts/library/{prompt_id}")
        assert second_del.status_code == 404, (
            f"Expected 404 on double-delete, got {second_del.status_code}"
        )

    async def test_options_preflight_request(self, client):
        """OPTIONS preflight request returns proper CORS headers."""
        # A proper CORS preflight requires Origin + Access-Control-Request-Method
        resp = await client.options(
            "/api/v1/prompts/library",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        # CORSMiddleware intercepts OPTIONS preflight and returns 200
        assert resp.status_code in (200, 204), (
            f"Expected 200 or 204 for OPTIONS preflight, got {resp.status_code}"
        )
        # Must include allow-origin in preflight response
        assert resp.headers.get("access-control-allow-origin") is not None, (
            "Preflight response missing access-control-allow-origin header"
        )

    async def test_prompt_text_with_html_characters(self, client):
        """Prompt text with HTML-like characters is stored verbatim (no escaping)."""
        html_text = '<div class="art">Draw a <b>bold</b> cat & "dog"</div>'
        resp = await _create_prompt(
            client,
            name="HTML Chars",
            promptText=html_text,
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["promptText"] == html_text, (
            f"HTML chars were modified: expected {html_text!r}, got {body['promptText']!r}"
        )
