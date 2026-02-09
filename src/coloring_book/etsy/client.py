"""Etsy API v3 client with OAuth 2.0 authentication."""

from __future__ import annotations

import hashlib
import logging
import secrets
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


class EtsyClient:
    """Etsy API v3 client with OAuth 2.0."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_uri: str = "http://localhost:5000/api/v1/etsy/callback",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.tokens: Optional[TokenResponse] = None
        self._code_verifier: Optional[str] = None

    def get_auth_url(self, scopes: Optional[list[str]] = None) -> tuple[str, str]:
        """Generate OAuth authorization URL with PKCE.

        Args:
            scopes: OAuth scopes (defaults to listings_w, listings_r, shops_r)

        Returns:
            Tuple of (auth_url, state)
        """
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
        """
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "code": code,
            "code_verifier": self._code_verifier or "",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(ETSY_TOKEN_URL, data=payload)
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
        """
        if not self.tokens:
            raise RuntimeError("No tokens to refresh. Authenticate first.")

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.api_key,
            "refresh_token": self.tokens.refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(ETSY_TOKEN_URL, data=payload)
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
        """Get authorization headers."""
        if not self.tokens:
            raise RuntimeError("Not authenticated. Call exchange_code first.")
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "x-api-key": self.api_key,
        }

    async def _ensure_valid_token(self) -> None:
        """Auto-refresh token if expired."""
        if self.tokens and self.tokens.is_expired:
            logger.info("Access token expired, refreshing...")
            await self.refresh_token()

    async def get_shop(self, shop_id: int) -> dict:
        """Get shop details."""
        await self._ensure_valid_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ETSY_BASE_URL}/application/shops/{shop_id}",
                headers=self._auth_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_me(self) -> dict:
        """Get authenticated user info."""
        await self._ensure_valid_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
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

        async with httpx.AsyncClient() as client:
            response = await client.post(
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

        async with httpx.AsyncClient() as client:
            response = await client.post(
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

        async with httpx.AsyncClient() as client:
            response = await client.post(
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
