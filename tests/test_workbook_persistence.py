"""Tests for WorkbookModel database persistence.

Validates that workbook CRUD operations correctly persist to and read from
the SQLAlchemy database layer, using the same in-memory SQLite test pattern
as test_api_endpoints.py.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from coloring_book.api.models import Base, WorkbookModel


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database session for each test."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSession()

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)


def _make_workbook(**overrides) -> WorkbookModel:
    """Create a WorkbookModel instance with sensible defaults."""
    defaults = {
        "theme": "vehicles",
        "title": "Test Vehicles Workbook",
        "subtitle": "For Boys Ages 3-5",
        "age_min": 3,
        "age_max": 5,
        "page_count": 30,
        "items_json": ["fire_truck", "police_car", "ambulance"],
        "activity_mix_json": {"trace_and_color": 10, "which_different": 5},
        "page_size": "letter",
        "status": "draft",
    }
    defaults.update(overrides)
    return WorkbookModel(**defaults)


class TestWorkbookPersistence:
    def test_create_workbook_persists_to_db(self, db_session):
        """A new WorkbookModel added to the session is persisted and gets an ID."""
        wb = _make_workbook(title="Persist Test")
        db_session.add(wb)
        db_session.commit()

        # ID should be auto-generated (UUID)
        assert wb.id is not None
        assert len(wb.id) == 36  # UUID format: 8-4-4-4-12

        # Verify it exists in the DB
        result = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb.id
        ).first()
        assert result is not None
        assert result.title == "Persist Test"
        assert result.theme == "vehicles"
        assert result.age_min == 3
        assert result.age_max == 5
        assert result.page_count == 30
        assert result.items_json == ["fire_truck", "police_car", "ambulance"]
        assert result.activity_mix_json == {"trace_and_color": 10, "which_different": 5}
        assert result.page_size == "letter"
        assert result.status == "draft"
        assert result.created_at is not None

    def test_get_workbook_by_id(self, db_session):
        """A workbook can be fetched by its primary key ID."""
        wb = _make_workbook(title="Fetch Test")
        db_session.add(wb)
        db_session.commit()
        wb_id = wb.id

        # Expire to force re-read from DB
        db_session.expire_all()

        fetched = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb_id
        ).first()
        assert fetched is not None
        assert fetched.id == wb_id
        assert fetched.title == "Fetch Test"
        assert fetched.subtitle == "For Boys Ages 3-5"
        assert fetched.items_json == ["fire_truck", "police_car", "ambulance"]

    def test_update_workbook_status(self, db_session):
        """Updating a workbook's status field persists the change."""
        wb = _make_workbook(title="Status Test")
        db_session.add(wb)
        db_session.commit()
        wb_id = wb.id

        # Update status
        wb.status = "generating"
        wb.progress = 0.5
        db_session.commit()

        # Expire and re-read
        db_session.expire_all()
        updated = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb_id
        ).first()
        assert updated.status == "generating"
        assert updated.progress == 0.5

        # Update to ready
        updated.status = "ready"
        updated.progress = 1.0
        db_session.commit()

        db_session.expire_all()
        final = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb_id
        ).first()
        assert final.status == "ready"
        assert final.progress == 1.0

    def test_delete_workbook(self, db_session):
        """Deleting a workbook removes it from the database."""
        wb = _make_workbook(title="Delete Test")
        db_session.add(wb)
        db_session.commit()
        wb_id = wb.id

        # Verify it exists
        assert db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb_id
        ).first() is not None

        # Delete it
        db_session.delete(wb)
        db_session.commit()

        # Verify it's gone
        result = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb_id
        ).first()
        assert result is None

    def test_list_workbooks_returns_all(self, db_session):
        """Querying all workbooks returns every persisted record."""
        # Start with empty
        all_wbs = db_session.query(WorkbookModel).all()
        assert len(all_wbs) == 0

        # Add multiple workbooks
        wb1 = _make_workbook(title="Workbook One")
        wb2 = _make_workbook(title="Workbook Two", theme="animals")
        wb3 = _make_workbook(title="Workbook Three", page_count=50)
        db_session.add_all([wb1, wb2, wb3])
        db_session.commit()

        # Query all
        all_wbs = db_session.query(WorkbookModel).all()
        assert len(all_wbs) == 3

        titles = {wb.title for wb in all_wbs}
        assert titles == {"Workbook One", "Workbook Two", "Workbook Three"}

        # Verify each has unique IDs
        ids = [wb.id for wb in all_wbs]
        assert len(ids) == len(set(ids))

    def test_workbook_json_fields_persist_complex_data(self, db_session):
        """JSON fields (items_json, activity_mix_json) correctly persist complex structures."""
        items = ["cat", "dog", "elephant", "giraffe", "lion"]
        activity_mix = {
            "trace_and_color": 10,
            "which_different": 5,
            "count_circle": 3,
            "match": 2,
        }
        wb = _make_workbook(
            title="JSON Test",
            items_json=items,
            activity_mix_json=activity_mix,
        )
        db_session.add(wb)
        db_session.commit()

        db_session.expire_all()
        fetched = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb.id
        ).first()
        assert fetched.items_json == items
        assert fetched.activity_mix_json == activity_mix

    def test_workbook_nullable_fields(self, db_session):
        """Nullable fields (subtitle, progress, pdf_path, etsy_listing_id) default correctly."""
        wb = WorkbookModel(
            theme="vehicles",
            title="Nullable Test",
        )
        db_session.add(wb)
        db_session.commit()

        db_session.expire_all()
        fetched = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb.id
        ).first()
        assert fetched.subtitle is None
        assert fetched.progress is None
        assert fetched.pdf_path is None
        assert fetched.etsy_listing_id is None
        assert fetched.status == "draft"
        assert fetched.age_min == 3
        assert fetched.age_max == 5
        assert fetched.page_count == 30

    def test_workbook_update_title_and_page_count(self, db_session):
        """Updating multiple fields in a single commit persists all changes."""
        wb = _make_workbook(title="Original Title", page_count=10)
        db_session.add(wb)
        db_session.commit()
        wb_id = wb.id

        wb.title = "Updated Title"
        wb.page_count = 50
        wb.subtitle = "New Subtitle"
        db_session.commit()

        db_session.expire_all()
        updated = db_session.query(WorkbookModel).filter(
            WorkbookModel.id == wb_id
        ).first()
        assert updated.title == "Updated Title"
        assert updated.page_count == 50
        assert updated.subtitle == "New Subtitle"
