"""Etsy listing management for workbooks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .client import EtsyClient, EtsyListing
from .seo import EtsySEOEngine
from ..workbook.models import WorkbookConfig

logger = logging.getLogger(__name__)


@dataclass
class ListingMetadata:
    """Auto-generated metadata for an Etsy listing."""

    title: str
    description: str
    price: float
    tags: list[str]


class EtsyListingService:
    """Create and manage Etsy listings for workbooks."""

    def __init__(self, client: EtsyClient, shop_id: int):
        self.client = client
        self.shop_id = shop_id
        self.seo = EtsySEOEngine()

    def build_listing_metadata(self, config: WorkbookConfig) -> ListingMetadata:
        """Generate Etsy-optimized metadata from workbook config.

        Returns:
            ListingMetadata with title, description, tags, price
        """
        return ListingMetadata(
            title=self.seo.generate_title(config),
            description=self.seo.generate_description(config),
            price=self.seo.suggest_price(config),
            tags=self.seo.generate_tags(config),
        )

    async def create_listing(
        self,
        config: WorkbookConfig,
        pdf_bytes: bytes,
        cover_image: Optional[bytes] = None,
        preview_images: Optional[list[bytes]] = None,
        price_override: Optional[float] = None,
    ) -> EtsyListing:
        """Create a complete Etsy listing for a workbook.

        Steps:
        1. Generate listing metadata from config
        2. Create draft listing on Etsy
        3. Upload PDF as digital file
        4. Upload cover as listing image
        5. Upload preview pages as additional images (Etsy allows 10)

        Args:
            config: Workbook configuration
            pdf_bytes: Generated PDF content
            cover_image: Cover page PNG (optional)
            preview_images: Preview page PNGs (optional, max 9)
            price_override: Override auto-suggested price

        Returns:
            EtsyListing with listing ID and details
        """
        # 1. Generate metadata
        metadata = self.build_listing_metadata(config)
        price = price_override if price_override is not None else metadata.price

        logger.info(f"Creating Etsy listing: {metadata.title} at ${price}")

        # 2. Create draft listing
        listing = await self.client.create_draft_listing(
            shop_id=self.shop_id,
            title=metadata.title,
            description=metadata.description,
            price=price,
            tags=metadata.tags,
            who_made="i_did",
            is_supply=False,
            when_made="made_to_order",
            is_digital=True,
        )

        logger.info(f"Draft listing created: {listing.listing_id}")

        # 3. Upload PDF as digital file
        await self.client.upload_listing_file(
            shop_id=self.shop_id,
            listing_id=listing.listing_id,
            file_data=pdf_bytes,
            filename=f"{config.title.replace(' ', '_')}.pdf",
        )

        # 4. Upload cover as listing image
        if cover_image:
            await self.client.upload_listing_image(
                shop_id=self.shop_id,
                listing_id=listing.listing_id,
                image_data=cover_image,
                rank=1,
            )

        # 5. Upload preview images (Etsy allows 10 images total)
        if preview_images:
            for i, preview in enumerate(preview_images[:9]):  # 9 + 1 cover = 10
                await self.client.upload_listing_image(
                    shop_id=self.shop_id,
                    listing_id=listing.listing_id,
                    image_data=preview,
                    rank=i + 2,  # Start at 2 (cover is rank 1)
                )

        logger.info(f"Listing {listing.listing_id} fully created with files and images")
        return listing

    async def update_listing_metadata(
        self,
        listing_id: int,
        metadata: ListingMetadata,
    ) -> dict:
        """Update an existing listing's metadata.

        Note: Etsy API v3 uses PUT for listing updates.
        """
        await self.client._ensure_valid_token()
        import httpx

        payload = {
            "title": metadata.title[:140],
            "description": metadata.description,
            "price": metadata.price,
            "tags": metadata.tags[:13],
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://api.etsy.com/v3/application/shops/{self.shop_id}/listings/{listing_id}",
                headers=self.client._auth_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
