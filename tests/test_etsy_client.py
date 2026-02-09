"""Tests for Etsy API client."""

import pytest

from coloring_book.etsy.client import (
    DIGITAL_DOWNLOADS_TAXONOMY,
    ETSY_AUTH_URL,
    EtsyClient,
    EtsyListing,
    TokenResponse,
)


class TestTokenResponse:
    def test_creation(self):
        token = TokenResponse(
            access_token="abc123",
            refresh_token="refresh456",
        )
        assert token.access_token == "abc123"
        assert token.refresh_token == "refresh456"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600

    def test_not_expired_initially(self):
        token = TokenResponse(
            access_token="abc", refresh_token="ref",
        )
        assert token.is_expired is False

    def test_expired_after_time(self):
        from datetime import datetime, timezone, timedelta
        token = TokenResponse(
            access_token="abc", refresh_token="ref",
            expires_in=10,
            issued_at=datetime.now(timezone.utc) - timedelta(seconds=20),
        )
        assert token.is_expired is True


class TestEtsyListing:
    def test_creation(self):
        listing = EtsyListing(
            listing_id=12345,
            title="Test Listing",
            description="A test listing",
            price=4.99,
            state="draft",
        )
        assert listing.listing_id == 12345
        assert listing.state == "draft"
        assert listing.taxonomy_id == DIGITAL_DOWNLOADS_TAXONOMY


class TestEtsyClient:
    def test_init(self):
        client = EtsyClient(api_key="key123", api_secret="secret456")
        assert client.api_key == "key123"
        assert client.api_secret == "secret456"
        assert client.is_authenticated is False

    def test_get_auth_url(self):
        client = EtsyClient(api_key="key123", api_secret="secret456")
        url, state = client.get_auth_url()

        assert ETSY_AUTH_URL in url
        assert "key123" in url
        assert "response_type=code" in url
        assert "code_challenge" in url
        assert len(state) > 10

    def test_get_auth_url_custom_scopes(self):
        client = EtsyClient(api_key="key123", api_secret="secret456")
        url, _ = client.get_auth_url(scopes=["listings_r"])

        assert "listings_r" in url

    def test_get_auth_url_generates_code_verifier(self):
        client = EtsyClient(api_key="key123", api_secret="secret456")
        assert client._code_verifier is None

        client.get_auth_url()
        assert client._code_verifier is not None
        assert len(client._code_verifier) > 20

    def test_auth_headers_raises_when_not_authenticated(self):
        client = EtsyClient(api_key="key123", api_secret="secret456")
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client._auth_headers()

    def test_auth_headers_with_tokens(self):
        client = EtsyClient(api_key="key123", api_secret="secret456")
        client.tokens = TokenResponse(
            access_token="token_abc", refresh_token="refresh_xyz",
        )
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer token_abc"
        assert headers["x-api-key"] == "key123"

    def test_is_authenticated_false(self):
        client = EtsyClient(api_key="key", api_secret="secret")
        assert client.is_authenticated is False

    def test_is_authenticated_true(self):
        client = EtsyClient(api_key="key", api_secret="secret")
        client.tokens = TokenResponse(access_token="abc", refresh_token="ref")
        assert client.is_authenticated is True

    def test_disconnect(self):
        client = EtsyClient(api_key="key", api_secret="secret")
        client.tokens = TokenResponse(access_token="abc", refresh_token="ref")
        client._code_verifier = "verifier"

        client.disconnect()
        assert client.tokens is None
        assert client._code_verifier is None
        assert client.is_authenticated is False

    def test_refresh_token_raises_when_no_tokens(self):
        client = EtsyClient(api_key="key", api_secret="secret")
        with pytest.raises(RuntimeError, match="No tokens"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(client.refresh_token())

    def test_auth_url_state_unique(self):
        client = EtsyClient(api_key="key", api_secret="secret")
        _, state1 = client.get_auth_url()
        _, state2 = client.get_auth_url()
        assert state1 != state2
