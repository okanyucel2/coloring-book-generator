"""Etsy API v3 client with OAuth 2.0 authentication."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

ETSY_BASE_URL = "https://api.etsy.com/v3"
ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"

# Etsy taxonomy ID for digital downloads / printables
DIGITAL_DOWNLOADS_TAXONOMY = 69150467

# Rate-limit defaults
DEFAULT_RATE_LIMIT_MAX_RETRIES = 3
DEFAULT_RATE_LIMIT_BASE_DELAY = 1.0  # seconds


class EtsyConfigError(Exception):
    """Raised when Etsy API credentials are missing or invalid."""


class EtsyRateLimitError(Exception):
    """Raised when Etsy rate limit is hit after exhausting retries."""

    def __init__(self, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        msg = "Etsy API rate limit exceeded."
        if retry_after:
            msg += f" Retry after {retry_after:.0f} seconds."
        super().__init__(msg)


class EtsyAuthError(Exception):
    """Raised for OAuth authentication failures with user-friendly messages."""


@dataclass
class TokenResponse:
    """OAuth token response from Etsy."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.issued_at).total_seconds()
        return elapsed >= self.expires_in - 60  # 1 min buffer


@dataclass
class EtsyListing:
    """Represents an Etsy listing."""

    listing_id: int
    title: str
    description: str
    price: float
    state: str  # "draft", "active"
    url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    taxonomy_id: int = DIGITAL_DOWNLOADS_TAXONOMY


def _validate_api_key(api_key: str) -> None:
    """Validate that an Etsy API key is configured.

    Raises:
        EtsyConfigError: When the API key is empty or a placeholder.
    """
    if not api_key:
        raise EtsyConfigError(
            "Etsy API key is not configured. "
            "Set the ETSY_API_KEY environment variable to your Etsy v3 API key. "
            "You can create one at https://www.etsy.com/developers/your-apps"
        )
    if api_key in ("your_key_here", "placeholder", "test"):
        raise EtsyConfigError(
            "Etsy API key appears to be a placeholder value. "
            "Replace it with your actual Etsy v3 API key."
        )


class EtsyClient:
    """Etsy API v3 client with OAuth 2.0.

    Features:
    - PKCE-based OAuth 2.0 flow
    - Automatic token refresh
    - Rate limit handling with exponential backoff
    - Graceful error messages for common failures
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_uri: str = "http://localhost:5000/api/v1/etsy/callback",
        rate_limit_max_retries: int = DEFAULT_RATE_LIMIT_MAX_RETRIES,
        rate_limit_base_delay: float = DEFAULT_RATE_LIMIT_BASE_DELAY,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.tokens: Optional[TokenResponse] = None
        self._code_verifier: Optional[str] = None
        self._rate_limit_max_retries = rate_limit_max_retries
        self._rate_limit_base_delay = rate_limit_base_delay

    def get_auth_url(self, scopes: Optional[list[str]] = None) -> tuple[str, str]:
        """Generate OAuth authorization URL with PKCE.

        Args:
            scopes: OAuth scopes (defaults to listings_w, listings_r, shops_r)

        Returns:
            Tuple of (auth_url, state)

        Raises:
            EtsyConfigError: If API key is not configured.
        """
        _validate_api_key(self.api_key)

        if scopes is None:
            scopes = ["listings_w", "listings_r", "shops_r"]

        # Generate PKCE challenge
        self._code_verifier = secrets.token_urlsafe(64)
        code_challenge = hashlib.sha256(
            self._code_verifier.encode()
        ).hexdigest()

        state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        url = f"{ETSY_AUTH_URL}?{urlencode(params)}"
        return url, state

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for access + refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            EtsyAuthError: If the code exchange fails.
        """
        _validate_api_key(self.api_key)

        payload = {
            "grant_type": "authorization_code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "code": code,
            "code_verifier": self._code_verifier or "",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(ETSY_TOKEN_URL, data=payload)
        except httpx.ConnectError:
            raise EtsyAuthError(
                "Cannot reach Etsy servers. Check your internet connection."
            )
        except httpx.TimeoutException:
            raise EtsyAuthError(
                "Etsy server did not respond in time. Please try again."
            )

        if response.status_code == 400:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            error_desc = error_data.get("error_description", "")
            if "invalid_grant" in str(error_data.get("error", "")) or "expired" in error_desc.lower():
                raise EtsyAuthError(
                    "Authorization code has expired or was already used. "
                    "Please start the OAuth flow again."
                )
            if "invalid_client" in str(error_data.get("error", "")):
                raise EtsyAuthError(
                    "Invalid API credentials. Verify your ETSY_API_KEY and ETSY_API_SECRET."
                )
            raise EtsyAuthError(
                f"OAuth token exchange failed: {error_desc or response.text}"
            )

        if response.status_code == 401:
            raise EtsyAuthError(
                "Etsy rejected the API credentials. "
                "Verify your ETSY_API_KEY is correct and the app is active."
            )

        if response.status_code == 403:
            raise EtsyAuthError(
                "Your Etsy app does not have the required permissions. "
                "Check that your app has the necessary scopes enabled."
            )

        if response.status_code == 429:
            retry_after = _parse_retry_after(response)
            raise EtsyRateLimitError(retry_after=retry_after)

        response.raise_for_status()
        data = response.json()

        self.tokens = TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
        )
        return self.tokens

    async def refresh_token(self) -> TokenResponse:
        """Refresh an expired access token.

        Returns:
            New TokenResponse

        Raises:
            EtsyAuthError: If the refresh fails.
        """
        if not self.tokens:
            raise EtsyAuthError(
                "No tokens available to refresh. Please authenticate first "
                "by completing the OAuth flow."
            )

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.api_key,
            "refresh_token": self.tokens.refresh_token,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(ETSY_TOKEN_URL, data=payload)
        except httpx.ConnectError:
            raise EtsyAuthError(
                "Cannot reach Etsy servers during token refresh. "
                "Check your internet connection."
            )
        except httpx.TimeoutException:
            raise EtsyAuthError(
                "Etsy server timed out during token refresh. Please try again."
            )

        if response.status_code == 400:
            error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            if "invalid_grant" in str(error_data.get("error", "")):
                self.tokens = None  # Clear invalid tokens
                raise EtsyAuthError(
                    "Refresh token is invalid or expired. "
                    "You need to re-authenticate with Etsy."
                )
            raise EtsyAuthError(
                f"Token refresh failed: {error_data.get('error_description', response.text)}"
            )

        if response.status_code == 429:
            retry_after = _parse_retry_after(response)
            raise EtsyRateLimitError(retry_after=retry_after)

        response.raise_for_status()
        data = response.json()

        self.tokens = TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 3600),
        )
        return self.tokens

    def _auth_headers(self) -> dict[str, str]:
        """Get authorization headers.

        Raises:
            EtsyAuthError: If not authenticated.
        """
        if not self.tokens:
            raise EtsyAuthError(
                "Not authenticated with Etsy. "
                "Complete the OAuth flow first by visiting the auth URL."
            )
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "x-api-key": self.api_key,
        }

    async def _ensure_valid_token(self) -> None:
        """Auto-refresh token if expired."""
        if self.tokens and self.tokens.is_expired:
            logger.info("Access token expired, refreshing...")
            await self.refresh_token()

    async def _request_with_rate_limit(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with automatic rate-limit retry.

        Retries on 429 responses with exponential backoff, respecting
        the Retry-After header when present.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response on success

        Raises:
            EtsyRateLimitError: After exhausting retries.
            EtsyAuthError: On authentication failures.
        """
        last_response = None
        for attempt in range(self._rate_limit_max_retries + 1):
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)

            if response.status_code != 429:
                # Handle auth errors with helpful messages
                if response.status_code == 401:
                    raise EtsyAuthError(
                        "Etsy returned 401 Unauthorized. Your access token may have been "
                        "revoked. Please re-authenticate."
                    )
                if response.status_code == 403:
                    raise EtsyAuthError(
                        "Etsy returned 403 Forbidden. Your app may lack the required "
                        "scopes for this operation."
                    )
                return response

            last_response = response
            retry_after = _parse_retry_after(response)
            delay = retry_after or (self._rate_limit_base_delay * (2 ** attempt))

            if attempt < self._rate_limit_max_retries:
                logger.warning(
                    f"Etsy rate limit hit (attempt {attempt + 1}/{self._rate_limit_max_retries + 1}). "
                    f"Retrying in {delay:.1f}s..."
                )
                await _async_sleep(delay)
            else:
                logger.error(
                    f"Etsy rate limit exceeded after {self._rate_limit_max_retries + 1} attempts."
                )

        # All retries exhausted
        retry_after = _parse_retry_after(last_response) if last_response else None
        raise EtsyRateLimitError(retry_after=retry_after)

    async def get_shop(self, shop_id: int) -> dict:
        """Get shop details."""
        await self._ensure_valid_token()
        response = await self._request_with_rate_limit(
            "GET",
            f"{ETSY_BASE_URL}/application/shops/{shop_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get_me(self) -> dict:
        """Get authenticated user info."""
        await self._ensure_valid_token()
        response = await self._request_with_rate_limit(
            "GET",
            f"{ETSY_BASE_URL}/application/users/me",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def create_draft_listing(
        self,
        shop_id: int,
        title: str,
        description: str,
        price: float,
        taxonomy_id: int = DIGITAL_DOWNLOADS_TAXONOMY,
        tags: Optional[list[str]] = None,
        who_made: str = "i_did",
        is_supply: bool = False,
        when_made: str = "made_to_order",
        is_digital: bool = True,
    ) -> EtsyListing:
        """Create a draft listing on Etsy.

        Args:
            shop_id: Etsy shop ID
            title: Listing title (max 140 chars)
            description: Listing description
            price: Price in USD
            taxonomy_id: Etsy taxonomy ID
            tags: List of tags (max 13, each max 20 chars)
            who_made: "i_did", "someone_else", "collective"
            is_supply: Is this a supply/tool?
            when_made: When was it made?
            is_digital: Is this a digital download?

        Returns:
            EtsyListing object
        """
        await self._ensure_valid_token()

        # Enforce Etsy limits
        if tags:
            tags = [t[:20] for t in tags[:13]]

        payload = {
            "title": title[:140],
            "description": description,
            "price": price,
            "taxonomy_id": taxonomy_id,
            "tags": tags or [],
            "who_made": who_made,
            "is_supply": is_supply,
            "when_made": when_made,
            "is_digital": is_digital,
            "quantity": 999,  # Digital items
            "type": "download",
        }

        response = await self._request_with_rate_limit(
            "POST",
            f"{ETSY_BASE_URL}/application/shops/{shop_id}/listings",
            headers=self._auth_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return EtsyListing(
            listing_id=data["listing_id"],
            title=data.get("title", title),
            description=data.get("description", description),
            price=price,
            state=data.get("state", "draft"),
            url=data.get("url"),
            tags=tags or [],
            taxonomy_id=taxonomy_id,
        )

    async def upload_listing_file(
        self, shop_id: int, listing_id: int, file_data: bytes, filename: str
    ) -> dict:
        """Upload a digital file to a listing."""
        await self._ensure_valid_token()

        response = await self._request_with_rate_limit(
            "POST",
            f"{ETSY_BASE_URL}/application/shops/{shop_id}/listings/{listing_id}/files",
            headers=self._auth_headers(),
            files={"file": (filename, file_data, "application/pdf")},
        )
        response.raise_for_status()
        return response.json()

    async def upload_listing_image(
        self, shop_id: int, listing_id: int, image_data: bytes, rank: int = 1
    ) -> dict:
        """Upload an image to a listing."""
        await self._ensure_valid_token()

        response = await self._request_with_rate_limit(
            "POST",
            f"{ETSY_BASE_URL}/application/shops/{shop_id}/listings/{listing_id}/images",
            headers=self._auth_headers(),
            files={"image": ("image.png", image_data, "image/png")},
            data={"rank": str(rank)},
        )
        response.raise_for_status()
        return response.json()

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid tokens."""
        return self.tokens is not None

    def disconnect(self) -> None:
        """Clear stored tokens."""
        self.tokens = None
        self._code_verifier = None


def _parse_retry_after(response: Optional[httpx.Response]) -> Optional[float]:
    """Parse the Retry-After header from an HTTP response.

    Returns seconds to wait, or None if header is not present.
    """
    if response is None:
        return None
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except (ValueError, TypeError):
        return None


async def _async_sleep(seconds: float) -> None:
    """Async sleep helper (allows easier mocking in tests)."""
    import asyncio
    await asyncio.sleep(seconds)
