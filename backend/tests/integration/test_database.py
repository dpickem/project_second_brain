"""
Integration Tests for Database Models and Operations

Tests database connectivity, model CRUD operations, and relationships.
Requires a running PostgreSQL instance.

Run with: pytest tests/integration/test_database.py -v
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Annotation,
    Content,
    ContentStatus,
    Tag,
)
from app.db.models_learning import (
    MasterySnapshot,
    PracticeAttempt,
    PracticeSession,
    SpacedRepCard,
)


def make_content_uuid() -> str:
    """Generate a unique content_uuid for testing."""
    return str(uuid.uuid4())


class TestDatabaseConnection:
    """Test PostgreSQL connectivity and basic operations."""

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session: AsyncSession) -> None:
        """Should be able to connect to the database."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_database_version(self, db_session: AsyncSession) -> None:
        """Should be connected to PostgreSQL 16+."""
        result = await db_session.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version

    @pytest.mark.asyncio
    async def test_tables_exist(self, db_session: AsyncSession) -> None:
        """All expected tables should exist."""
        expected_models = [
            Content,
            Annotation,
            Tag,
            PracticeSession,
            PracticeAttempt,
            SpacedRepCard,
            MasterySnapshot,
        ]

        for model in expected_models:
            table_name = model.__tablename__
            result = await db_session.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = :table_name
                    )
                    """
                ),
                {"table_name": table_name},
            )
            exists = result.scalar()
            assert exists, f"Table '{table_name}' does not exist"


class TestContentModel:
    """Test Content model CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_content(self, clean_db: AsyncSession) -> None:
        """Should create a content record."""
        content = Content(
            content_uuid=make_content_uuid(),
            content_type="paper",
            title="Test Paper: Neural Networks",
            source_url="https://example.com/paper.pdf",
            status=ContentStatus.PENDING,
        )

        clean_db.add(content)
        await clean_db.commit()
        await clean_db.refresh(content)

        assert content.id is not None
        assert content.title == "Test Paper: Neural Networks"
        assert content.content_type == "paper"
        assert content.status == ContentStatus.PENDING

    @pytest.mark.asyncio
    async def test_query_content_by_type(self, clean_db: AsyncSession) -> None:
        """Should query content by content_type."""
        # Create test data
        paper = Content(
            content_uuid=make_content_uuid(), content_type="paper", title="Paper 1"
        )
        article = Content(
            content_uuid=make_content_uuid(), content_type="article", title="Article 1"
        )
        clean_db.add_all([paper, article])
        await clean_db.commit()

        # Query papers only
        result = await clean_db.execute(
            select(Content).where(Content.content_type == "paper")
        )
        papers = result.scalars().all()

        assert len(papers) == 1
        assert papers[0].title == "Paper 1"

    @pytest.mark.asyncio
    async def test_update_content_status(self, clean_db: AsyncSession) -> None:
        """Should update content status."""
        content = Content(
            content_uuid=make_content_uuid(),
            content_type="paper",
            title="Test Paper",
            status=ContentStatus.PENDING,
        )
        clean_db.add(content)
        await clean_db.commit()

        # Update status
        content.status = ContentStatus.PROCESSED
        content.processed_at = datetime.utcnow()
        await clean_db.commit()
        await clean_db.refresh(content)

        assert content.status == ContentStatus.PROCESSED
        assert content.processed_at is not None

    @pytest.mark.asyncio
    async def test_content_timestamps(self, clean_db: AsyncSession) -> None:
        """Content should have auto-populated timestamps."""
        content = Content(
            content_uuid=make_content_uuid(),
            content_type="article",
            title="Timestamped Article",
        )
        clean_db.add(content)
        await clean_db.commit()
        await clean_db.refresh(content)

        assert content.created_at is not None
        assert content.updated_at is not None
        assert content.created_at <= content.updated_at


class TestAnnotationModel:
    """Test Annotation model and its relationship to Content."""

    @pytest.mark.asyncio
    async def test_create_annotation(self, clean_db: AsyncSession) -> None:
        """Should create an annotation linked to content."""
        # Create parent content
        content = Content(
            content_uuid=make_content_uuid(),
            content_type="paper",
            title="Paper with Annotations",
        )
        clean_db.add(content)
        await clean_db.commit()

        # Create annotation
        annotation = Annotation(
            content_id=content.id,
            annotation_type="highlight",
            text="This is an important finding.",
            page_number=5,
        )
        clean_db.add(annotation)
        await clean_db.commit()
        await clean_db.refresh(annotation)

        assert annotation.id is not None
        assert annotation.content_id == content.id
        assert annotation.text == "This is an important finding."

    @pytest.mark.asyncio
    async def test_content_annotation_relationship(
        self, clean_db: AsyncSession
    ) -> None:
        """Should access annotations through content relationship."""
        content = Content(
            content_uuid=make_content_uuid(),
            content_type="book",
            title="Book with Highlights",
        )
        clean_db.add(content)
        await clean_db.commit()

        # Add multiple annotations
        annotations = [
            Annotation(
                content_id=content.id,
                annotation_type="highlight",
                text=f"Highlight {i}",
            )
            for i in range(3)
        ]
        clean_db.add_all(annotations)
        await clean_db.commit()

        # Refresh and access via relationship
        await clean_db.refresh(content)

        # Note: Need to use selectin load or explicit join for async
        result = await clean_db.execute(
            select(Annotation).where(Annotation.content_id == content.id)
        )
        loaded_annotations = result.scalars().all()

        assert len(loaded_annotations) == 3


class TestTagModel:
    """Test Tag model operations."""

    @pytest.mark.asyncio
    async def test_create_tag(self, clean_db: AsyncSession) -> None:
        """Should create a tag."""
        tag = Tag(
            name="ml/transformers",
            description="Machine learning transformer architecture",
        )
        clean_db.add(tag)
        await clean_db.commit()
        await clean_db.refresh(tag)

        assert tag.id is not None
        assert tag.name == "ml/transformers"

    @pytest.mark.asyncio
    async def test_tag_name_unique(self, clean_db: AsyncSession) -> None:
        """Tag names should be unique."""
        tag1 = Tag(name="unique/tag")
        clean_db.add(tag1)
        await clean_db.commit()

        tag2 = Tag(name="unique/tag")  # Duplicate
        clean_db.add(tag2)

        with pytest.raises(IntegrityError):
            await clean_db.commit()


class TestPracticeSessionModel:
    """Test PracticeSession and PracticeAttempt models."""

    @pytest.mark.asyncio
    async def test_create_practice_session(self, clean_db: AsyncSession) -> None:
        """Should create a practice session."""
        session = PracticeSession(
            session_type="review",
            total_cards=10,
            correct_count=8,
        )
        clean_db.add(session)
        await clean_db.commit()
        await clean_db.refresh(session)

        assert session.id is not None
        assert session.session_type == "review"
        assert session.started_at is not None

    @pytest.mark.asyncio
    async def test_end_practice_session(self, clean_db: AsyncSession) -> None:
        """Should record session end time."""
        session = PracticeSession(session_type="quiz")
        clean_db.add(session)
        await clean_db.commit()

        # End the session
        session.ended_at = datetime.utcnow()
        await clean_db.commit()
        await clean_db.refresh(session)

        assert session.ended_at is not None
        assert session.ended_at >= session.started_at


class TestSpacedRepCardModel:
    """Test SpacedRepCard model for spaced repetition."""

    @pytest.mark.asyncio
    async def test_create_card(self, clean_db: AsyncSession) -> None:
        """Should create a spaced repetition card."""
        card = SpacedRepCard(
            card_type="concept",
            front="What is attention in transformers?",
            back="Attention is a mechanism that allows the model to focus on relevant parts of the input.",
        )
        clean_db.add(card)
        await clean_db.commit()
        await clean_db.refresh(card)

        assert card.id is not None
        assert card.stability == 0.0  # FSRS default
        assert card.difficulty == 0.3  # FSRS default

    @pytest.mark.asyncio
    async def test_card_defaults(self, clean_db: AsyncSession) -> None:
        """Cards should have sensible FSRS defaults."""
        card = SpacedRepCard(
            card_type="question",
            front="Q",
            back="A",
        )
        clean_db.add(card)
        await clean_db.commit()
        await clean_db.refresh(card)

        assert card.stability == 0.0  # FSRS: memory stability in days
        assert card.difficulty == 0.3  # FSRS: difficulty 0-1
        assert card.scheduled_days == 0  # FSRS: days until next review
        assert card.repetitions == 0
        assert card.total_reviews == 0
        assert card.correct_reviews == 0

    @pytest.mark.asyncio
    async def test_card_linked_to_content(self, clean_db: AsyncSession) -> None:
        """Cards can be linked to source content."""
        content_uuid = make_content_uuid()
        content = Content(
            content_uuid=content_uuid, content_type="paper", title="Source Paper"
        )
        clean_db.add(content)
        await clean_db.commit()

        card = SpacedRepCard(
            content_id=content_uuid,  # UUID string for the app-facing identifier
            source_content_pk=content.id,  # Integer FK for ORM relationship
            card_type="concept",
            front="Question from paper",
            back="Answer from paper",
        )
        clean_db.add(card)
        await clean_db.commit()
        await clean_db.refresh(card)

        assert card.content_id == content_uuid
        assert card.source_content_pk == content.id


class TestMasterySnapshotModel:
    """Test MasterySnapshot model for progress tracking."""

    @pytest.mark.asyncio
    async def test_create_mastery_snapshot(self, clean_db: AsyncSession) -> None:
        """Should create a mastery snapshot."""
        snapshot = MasterySnapshot(
            total_cards=50,
            mastered_cards=30,
            learning_cards=15,
            new_cards=5,
            mastery_score=60.0,
        )
        clean_db.add(snapshot)
        await clean_db.commit()
        await clean_db.refresh(snapshot)

        assert snapshot.id is not None
        assert snapshot.mastery_score == 60.0
        assert snapshot.snapshot_date is not None

    @pytest.mark.asyncio
    async def test_mastery_snapshot_by_date(self, clean_db: AsyncSession) -> None:
        """Should query snapshots by date range."""
        # Create snapshots for multiple days
        today = datetime.utcnow()
        snapshots = [
            MasterySnapshot(
                snapshot_date=today - timedelta(days=i),
                mastery_score=50.0 + i * 5,
            )
            for i in range(7)
        ]
        clean_db.add_all(snapshots)
        await clean_db.commit()

        # Query last 3 days
        three_days_ago = today - timedelta(days=3)
        result = await clean_db.execute(
            select(MasterySnapshot).where(
                MasterySnapshot.snapshot_date >= three_days_ago
            )
        )
        recent_snapshots = result.scalars().all()

        assert len(recent_snapshots) >= 3


class TestDatabaseTransactions:
    """Test transaction behavior."""

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, db_session: AsyncSession) -> None:
        """Should rollback transaction on error."""
        table_name = Content.__tablename__

        initial_count_result = await db_session.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        )
        initial_count = initial_count_result.scalar()

        try:
            content = Content(
                content_uuid=make_content_uuid(),
                content_type="test",
                title="Will be rolled back",
            )
            db_session.add(content)
            # Don't commit, just let the session rollback
            raise ValueError("Simulated error")
        except ValueError:
            await db_session.rollback()

        final_count_result = await db_session.execute(
            text(f"SELECT COUNT(*) FROM {table_name}")
        )
        final_count = final_count_result.scalar()

        assert final_count == initial_count
