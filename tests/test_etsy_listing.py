"""Tests for Etsy listing service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from coloring_book.etsy.client import EtsyClient, EtsyListing, TokenResponse
from coloring_book.etsy.listing import EtsyListingService, ListingMetadata
from coloring_book.etsy.seo import EtsySEOEngine
from coloring_book.workbook.models import WorkbookConfig


def _make_config(**overrides) -> WorkbookConfig:
    defaults = {
        "theme": "vehicles",
        "title": "Test Vehicles Workbook",
        "subtitle": "Ages 3-5",
        "age_range": (3, 5),
        "page_count": 30,
        "items": ["fire_truck", "police_car", "ambulance"],
        "activity_mix": {
            "trace_and_color": 18,
            "which_different": 2,
            "count_circle": 2,
            "match": 2,
            "word_to_image": 1,
            "find_circle": 2,
        },
        "page_size": "letter",
    }
    defaults.update(overrides)
    return WorkbookConfig(**defaults)


class TestListingMetadata:
    def test_creation(self):
        meta = ListingMetadata(
            title="Test Title",
            description="Test description",
            price=4.99,
            tags=["tag1", "tag2"],
        )
        assert meta.title == "Test Title"
        assert meta.price == 4.99
        assert len(meta.tags) == 2


class TestEtsyListingService:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock(spec=EtsyClient)
        client.tokens = TokenResponse(access_token="test", refresh_token="ref")
        client._auth_headers.return_value = {
            "Authorization": "Bearer test",
            "x-api-key": "key",
        }
        client._ensure_valid_token = AsyncMock()
        client.create_draft_listing = AsyncMock(return_value=EtsyListing(
            listing_id=99999,
            title="Test",
            description="Desc",
            price=4.99,
            state="draft",
        ))
        client.upload_listing_file = AsyncMock(return_value={"file_id": 1})
        client.upload_listing_image = AsyncMock(return_value={"image_id": 1})
        return client

    @pytest.fixture
    def service(self, mock_client):
        return EtsyListingService(client=mock_client, shop_id=12345)

    def test_build_listing_metadata(self, service):
        config = _make_config()
        metadata = service.build_listing_metadata(config)

        assert isinstance(metadata, ListingMetadata)
        assert "Vehicles" in metadata.title
        assert len(metadata.tags) <= 13
        assert metadata.price > 0
        assert len(metadata.description) > 100

    def test_build_listing_metadata_animals(self, service):
        config = _make_config(theme="animals")
        metadata = service.build_listing_metadata(config)
        assert "Animals" in metadata.title

    @pytest.mark.asyncio
    async def test_create_listing(self, service, mock_client):
        config = _make_config()
        pdf_bytes = b"%PDF-1.4 test content"
        cover = b"\x89PNG cover"
        previews = [b"\x89PNG page1", b"\x89PNG page2"]

        listing = await service.create_listing(
            config=config,
            pdf_bytes=pdf_bytes,
            cover_image=cover,
            preview_images=previews,
        )

        assert listing.listing_id == 99999
        assert listing.state == "draft"

        # Verify calls
        mock_client.create_draft_listing.assert_called_once()
        mock_client.upload_listing_file.assert_called_once()
        # Cover + 2 preview images = 3 image uploads
        assert mock_client.upload_listing_image.call_count == 3

    @pytest.mark.asyncio
    async def test_create_listing_no_images(self, service, mock_client):
        config = _make_config()
        pdf_bytes = b"%PDF-1.4 test"

        listing = await service.create_listing(
            config=config, pdf_bytes=pdf_bytes,
        )

        assert listing.listing_id == 99999
        mock_client.upload_listing_file.assert_called_once()
        mock_client.upload_listing_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_listing_price_override(self, service, mock_client):
        config = _make_config()
        pdf_bytes = b"%PDF-1.4"

        await service.create_listing(
            config=config, pdf_bytes=pdf_bytes, price_override=7.99,
        )

        call_kwargs = mock_client.create_draft_listing.call_args
        assert call_kwargs.kwargs["price"] == 7.99

    @pytest.mark.asyncio
    async def test_create_listing_max_9_previews(self, service, mock_client):
        config = _make_config()
        pdf_bytes = b"%PDF-1.4"
        # 15 preview images, should only upload 9
        previews = [b"\x89PNG" for _ in range(15)]

        await service.create_listing(
            config=config, pdf_bytes=pdf_bytes,
            cover_image=b"\x89PNG cover",
            preview_images=previews,
        )

        # 1 cover + 9 previews = 10 image uploads
        assert mock_client.upload_listing_image.call_count == 10

    @pytest.mark.asyncio
    async def test_create_listing_calls_digital(self, service, mock_client):
        config = _make_config()
        pdf_bytes = b"%PDF-1.4"

        await service.create_listing(config=config, pdf_bytes=pdf_bytes)

        call_kwargs = mock_client.create_draft_listing.call_args.kwargs
        assert call_kwargs["is_digital"] is True
        assert call_kwargs["who_made"] == "i_did"


class TestEtsyListingServiceIntegration:
    """Integration tests with real SEO engine."""

    def test_metadata_consistency(self):
        client = MagicMock(spec=EtsyClient)
        service = EtsyListingService(client=client, shop_id=123)
        config = _make_config()

        meta1 = service.build_listing_metadata(config)
        meta2 = service.build_listing_metadata(config)

        assert meta1.title == meta2.title
        assert meta1.price == meta2.price
        assert meta1.tags == meta2.tags
