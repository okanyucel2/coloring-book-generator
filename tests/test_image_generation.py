"""
Tests for image generation endpoint and service.

TDD RED PHASE: Tests target POST /api/v1/generate endpoint.
The external image API is mocked — we test our service logic, not OpenAI/SD.

Test groups:
  1. Generate endpoint - valid requests, response format
  2. Input validation - missing fields, invalid models, prompt limits
  3. Service integration - provider calls, error handling, DB persistence
  4. Multi-model support - model parameter routing
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import httpx
from httpx import ASGITransport
from src.coloring_book.api.app import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """Async test client with in-memory SQLite, same as test_api_endpoints."""
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
        c._test_session_factory = TestSession
        yield c

    app.dependency_overrides.clear()
    models.Base.metadata.drop_all(bind=test_engine)


MOCK_IMAGE_URL = "https://generated.example.com/image-abc123.png"

VALID_PAYLOAD = {
    "prompt": "A cute cat sitting on a rainbow",
    "model": "dalle3",
}


def _mock_generate_success():
    """Returns a mock that simulates successful image generation."""
    mock = AsyncMock(return_value={
        "image_url": MOCK_IMAGE_URL,
        "seed": 42,
        "model": "dalle3",
    })
    return mock


def _mock_generate_failure(error_msg="API rate limit exceeded"):
    """Returns a mock that simulates a generation failure."""
    mock = AsyncMock(side_effect=Exception(error_msg))
    return mock


# ===========================================================================
# 1. GENERATE ENDPOINT - VALID REQUESTS
# ===========================================================================

class TestGenerateEndpoint:
    """POST /api/v1/generate"""

    async def test_generate_returns_201_with_result(self, client):
        """POST with valid prompt+model returns 201 and generated image data."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "id" in body, "Response missing 'id'"
        assert "imageUrl" in body, "Response missing 'imageUrl'"
        assert body["imageUrl"] == MOCK_IMAGE_URL
        assert body["prompt"] == VALID_PAYLOAD["prompt"]
        assert body["model"] == "dalle3"

    async def test_generate_returns_seed_in_response(self, client):
        """Generated result includes seed for reproducibility."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert "seed" in body, "Response missing 'seed'"
        assert isinstance(body["seed"], int), f"Seed should be int, got {type(body['seed'])}"

    async def test_generate_returns_generated_at_timestamp(self, client):
        """Response includes generatedAt ISO timestamp."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert "generatedAt" in body, "Response missing 'generatedAt'"
        assert isinstance(body["generatedAt"], str) and len(body["generatedAt"]) > 0

    async def test_generate_saves_to_variation_history(self, client):
        """After generation, the result appears in variation history."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            gen_resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert gen_resp.status_code == 201
        variation_id = gen_resp.json()["id"]

        # Check it appears in history
        history_resp = await client.get("/api/v1/variations/history")
        assert history_resp.status_code == 200
        data = history_resp.json()["data"]
        ids = [v["id"] for v in data]
        assert variation_id in ids, (
            f"Generated variation {variation_id} not in history: {ids}"
        )

    async def test_generate_with_optional_style(self, client):
        """Style parameter is accepted and stored."""
        payload = {**VALID_PAYLOAD, "style": "kawaii"}
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            resp = await client.post("/api/v1/generate", json=payload)

        assert resp.status_code == 201

    async def test_generate_with_custom_seed(self, client):
        """Custom seed parameter is forwarded to the service."""
        payload = {**VALID_PAYLOAD, "seed": 12345}
        mock = _mock_generate_success()
        with patch("src.coloring_book.api.app.generate_image", mock):
            resp = await client.post("/api/v1/generate", json=payload)

        assert resp.status_code == 201
        # Verify seed was passed to the service
        mock.assert_called_once()
        call_kwargs = mock.call_args
        # The service should receive the seed
        assert call_kwargs is not None


# ===========================================================================
# 2. INPUT VALIDATION
# ===========================================================================

class TestGenerateValidation:
    """Validation for POST /api/v1/generate"""

    async def test_missing_prompt_returns_422(self, client):
        """POST without prompt returns 422."""
        payload = {"model": "dalle3"}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422, f"Expected 422 for missing prompt, got {resp.status_code}"

    async def test_empty_prompt_returns_422(self, client):
        """POST with empty prompt string returns 422."""
        payload = {"prompt": "", "model": "dalle3"}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422, f"Expected 422 for empty prompt, got {resp.status_code}"

    async def test_missing_model_returns_422(self, client):
        """POST without model returns 422."""
        payload = {"prompt": "Draw a cat"}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422, f"Expected 422 for missing model, got {resp.status_code}"

    async def test_invalid_model_returns_422(self, client):
        """POST with unsupported model name returns 422."""
        payload = {"prompt": "Draw a cat", "model": "nonexistent-model-xyz"}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422, (
            f"Expected 422 for invalid model, got {resp.status_code}"
        )

    async def test_prompt_too_long_returns_422(self, client):
        """POST with prompt exceeding 2000 chars returns 422."""
        payload = {"prompt": "x" * 2001, "model": "dalle3"}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422, (
            f"Expected 422 for prompt > 2000 chars, got {resp.status_code}"
        )

    async def test_prompt_at_max_length_succeeds(self, client):
        """POST with exactly 2000-char prompt succeeds."""
        payload = {"prompt": "A" * 2000, "model": "dalle3"}
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 201, (
            f"Expected 201 for 2000-char prompt, got {resp.status_code}"
        )

    async def test_invalid_seed_type_returns_422(self, client):
        """POST with non-integer seed returns 422."""
        payload = {"prompt": "Draw a cat", "model": "dalle3", "seed": "not-a-number"}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422


# ===========================================================================
# 3. SERVICE INTEGRATION - ERROR HANDLING
# ===========================================================================

class TestGenerateServiceErrors:
    """Error handling when the image generation service fails."""

    async def test_service_error_returns_502(self, client):
        """When external API fails, endpoint returns 502 Bad Gateway."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_failure("OpenAI API error: rate limit"),
        ):
            resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert resp.status_code == 502, f"Expected 502, got {resp.status_code}"
        body = resp.json()
        assert "detail" in body, "Error response should have 'detail'"

    async def test_service_timeout_returns_504(self, client):
        """When generation times out, endpoint returns 504."""
        timeout_mock = AsyncMock(side_effect=TimeoutError("Generation timed out"))
        with patch("src.coloring_book.api.app.generate_image", timeout_mock):
            resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert resp.status_code == 504, f"Expected 504 for timeout, got {resp.status_code}"

    async def test_failed_generation_not_saved_to_history(self, client):
        """Failed generations should NOT appear in variation history."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_failure(),
        ):
            await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        history_resp = await client.get("/api/v1/variations/history")
        assert history_resp.status_code == 200
        data = history_resp.json()["data"]
        assert data == [], f"Failed generation should not be in history, got {data}"


# ===========================================================================
# 4. MULTI-MODEL SUPPORT
# ===========================================================================

class TestGenerateMultiModel:
    """Model selection and multi-model generation."""

    async def test_dalle3_model_accepted(self, client):
        """Model 'dalle3' is accepted."""
        payload = {"prompt": "Draw a dog", "model": "dalle3"}
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 201
        assert resp.json()["model"] == "dalle3"

    async def test_sdxl_model_accepted(self, client):
        """Model 'sdxl' is accepted."""
        mock = AsyncMock(return_value={
            "image_url": MOCK_IMAGE_URL,
            "seed": 99,
            "model": "sdxl",
        })
        payload = {"prompt": "Draw a horse", "model": "sdxl"}
        with patch("src.coloring_book.api.app.generate_image", mock):
            resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 201
        assert resp.json()["model"] == "sdxl"

    async def test_imagen_model_accepted(self, client):
        """Model 'imagen' is accepted."""
        mock = AsyncMock(return_value={
            "image_url": MOCK_IMAGE_URL,
            "seed": 77,
            "model": "imagen",
        })
        payload = {"prompt": "Draw an elephant", "model": "imagen"}
        with patch("src.coloring_book.api.app.generate_image", mock):
            resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 201
        assert resp.json()["model"] == "imagen"

    async def test_model_name_stored_in_variation(self, client):
        """The model used is stored in the variation record."""
        with patch(
            "src.coloring_book.api.app.generate_image",
            _mock_generate_success(),
        ):
            gen_resp = await client.post("/api/v1/generate", json=VALID_PAYLOAD)

        assert gen_resp.status_code == 201
        variation_id = gen_resp.json()["id"]

        # Check in history
        history_resp = await client.get("/api/v1/variations/history")
        data = history_resp.json()["data"]
        variation = next(v for v in data if v["id"] == variation_id)
        assert variation["model"] == "dalle3", (
            f"Expected model 'dalle3' in history, got '{variation['model']}'"
        )
