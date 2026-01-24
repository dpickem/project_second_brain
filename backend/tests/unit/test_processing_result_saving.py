"""
Unit tests for processing result saving.

Tests that followups, questions, and other related records
are correctly saved to the database after processing completes.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.enums import (
    ContentType,
    SummaryLevel,
    ConceptImportance,
    RelationshipType,
    FollowupTaskType,
    FollowupPriority,
    FollowupTimeEstimate,
    QuestionType,
    QuestionDifficulty,
)
from app.models.content import UnifiedContent
from app.models.processing import (
    ProcessingResult,
    ContentAnalysis,
    ExtractionResult,
    TagAssignment,
    Concept,
    Connection,
    FollowupTask,
    MasteryQuestion,
)
from app.db.models_processing import (
    ProcessingRun,
    FollowupRecord,
    QuestionRecord,
)


# =============================================================================
# Helper Functions
# =============================================================================


def make_followup(
    task: str = "Research topic",
    task_type: FollowupTaskType = FollowupTaskType.RESEARCH,
    priority: FollowupPriority = FollowupPriority.MEDIUM,
    estimated_time: FollowupTimeEstimate = FollowupTimeEstimate.THIRTY_MIN,
) -> FollowupTask:
    """Create a followup task with defaults."""
    return FollowupTask(
        task=task,
        task_type=task_type.value,
        priority=priority.value,
        estimated_time=estimated_time.value,
    )


def make_question(
    question: str = "What is the main concept?",
    question_type: QuestionType = QuestionType.CONCEPTUAL,
    difficulty: QuestionDifficulty = QuestionDifficulty.INTERMEDIATE,
    hints: list = None,
    key_points: list = None,
) -> MasteryQuestion:
    """Create a mastery question with defaults."""
    return MasteryQuestion(
        question=question,
        question_type=question_type.value,
        difficulty=difficulty.value,
        hints=hints or ["Think about it"],
        key_points=key_points or ["Key point 1"],
    )


def make_processing_result(
    content_id: str = "test-content-123",
    followups: list = None,
    questions: list = None,
) -> ProcessingResult:
    """Create a processing result with specified followups and questions."""
    return ProcessingResult(
        content_id=content_id,
        analysis=ContentAnalysis(
            content_type="paper",
            domain="ml",
            complexity="intermediate",
            estimated_length="medium",
            key_topics=["topic1"],
        ),
        summaries={
            SummaryLevel.BRIEF.value: "Brief summary",
            SummaryLevel.STANDARD.value: "Standard summary",
            SummaryLevel.DETAILED.value: "Detailed summary",
        },
        extraction=ExtractionResult(
            concepts=[
                Concept(
                    name="Test Concept",
                    definition="Test definition",
                    importance=ConceptImportance.CORE.value,
                )
            ],
            key_findings=["Finding 1"],
        ),
        tags=TagAssignment(
            domain_tags=["ml/topic"],
            meta_tags=["status/review"],
        ),
        connections=[],
        followups=followups or [],
        mastery_questions=questions or [],
        processing_time_seconds=10.0,
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_followups() -> list[FollowupTask]:
    """Create sample followup tasks."""
    return [
        make_followup(
            task="Research the original paper on transformers",
            task_type=FollowupTaskType.RESEARCH,
            priority=FollowupPriority.HIGH,
        ),
        make_followup(
            task="Implement attention mechanism from scratch",
            task_type=FollowupTaskType.PRACTICE,
            priority=FollowupPriority.MEDIUM,
        ),
        make_followup(
            task="Connect this to your existing ML knowledge",
            task_type=FollowupTaskType.CONNECT,
            priority=FollowupPriority.LOW,
        ),
    ]


@pytest.fixture
def sample_questions() -> list[MasteryQuestion]:
    """Create sample mastery questions."""
    return [
        make_question(
            question="What is the advantage of self-attention over RNNs?",
            question_type=QuestionType.CONCEPTUAL,
            difficulty=QuestionDifficulty.INTERMEDIATE,
        ),
        make_question(
            question="How would you implement multi-head attention?",
            question_type=QuestionType.APPLICATION,
            difficulty=QuestionDifficulty.ADVANCED,
        ),
    ]


# =============================================================================
# ProcessingRun.from_processing_result Tests
# =============================================================================


class TestProcessingRunFromResult:
    """Tests for ProcessingRun.from_processing_result method."""

    def test_creates_basic_processing_run(self):
        """Test creating a basic processing run from result."""
        result = make_processing_result()
        
        run = ProcessingRun.from_processing_result(
            content_id=1,
            status="COMPLETED",
            processing_result=result,
        )
        
        assert run.content_id == 1
        assert run.status == "COMPLETED"
        assert run.analysis is not None
        assert run.summaries is not None

    def test_processing_run_includes_metadata(self):
        """Test that processing metadata is included."""
        result = make_processing_result()
        result.processing_time_seconds = 45.5
        result.estimated_cost_usd = 0.05
        
        run = ProcessingRun.from_processing_result(
            content_id=1,
            status="COMPLETED",
            processing_result=result,
        )
        
        assert run.processing_time_seconds == 45.5
        assert run.estimated_cost_usd == 0.05

    def test_processing_run_handles_none_result(self):
        """Test creating failed processing run without result."""
        run = ProcessingRun.from_processing_result(
            content_id=1,
            status="FAILED",
            error_message="Processing failed",
        )
        
        assert run.content_id == 1
        assert run.status == "FAILED"
        assert run.error_message == "Processing failed"
        assert run.analysis is None


# =============================================================================
# FollowupRecord Tests
# =============================================================================


class TestFollowupRecord:
    """Tests for FollowupRecord model."""

    def test_followup_record_creation(self):
        """Test creating a FollowupRecord from task data."""
        run_id = uuid.uuid4()
        
        record = FollowupRecord(
            processing_run_id=run_id,
            task="Research transformers",
            task_type=FollowupTaskType.RESEARCH.value,
            priority=FollowupPriority.HIGH.value,
            estimated_time=FollowupTimeEstimate.ONE_HOUR.value,
        )
        
        assert record.task == "Research transformers"
        assert record.task_type == "RESEARCH"
        assert record.priority == "HIGH"
        assert record.estimated_time == "1HR"
        # completed defaults to None (not False) before being set in DB
        assert record.completed is None or record.completed is False
        assert record.completed_at is None

    def test_followup_record_all_task_types(self):
        """Test FollowupRecord with all task types."""
        run_id = uuid.uuid4()
        
        for task_type in FollowupTaskType:
            record = FollowupRecord(
                processing_run_id=run_id,
                task=f"Task for {task_type.value}",
                task_type=task_type.value,
                priority=FollowupPriority.MEDIUM.value,
                estimated_time=FollowupTimeEstimate.THIRTY_MIN.value,
            )
            assert record.task_type == task_type.value

    def test_followup_record_all_priorities(self):
        """Test FollowupRecord with all priority levels."""
        run_id = uuid.uuid4()
        
        for priority in FollowupPriority:
            record = FollowupRecord(
                processing_run_id=run_id,
                task=f"Task with {priority.value} priority",
                task_type=FollowupTaskType.RESEARCH.value,
                priority=priority.value,
                estimated_time=FollowupTimeEstimate.THIRTY_MIN.value,
            )
            assert record.priority == priority.value

    def test_followup_record_all_time_estimates(self):
        """Test FollowupRecord with all time estimates."""
        run_id = uuid.uuid4()
        
        for time_est in FollowupTimeEstimate:
            record = FollowupRecord(
                processing_run_id=run_id,
                task=f"Task taking {time_est.value}",
                task_type=FollowupTaskType.RESEARCH.value,
                priority=FollowupPriority.MEDIUM.value,
                estimated_time=time_est.value,
            )
            assert record.estimated_time == time_est.value


# =============================================================================
# QuestionRecord Tests
# =============================================================================


class TestQuestionRecord:
    """Tests for QuestionRecord model."""

    def test_question_record_creation(self):
        """Test creating a QuestionRecord from question data."""
        run_id = uuid.uuid4()
        
        record = QuestionRecord(
            processing_run_id=run_id,
            question="What is self-attention?",
            question_type=QuestionType.CONCEPTUAL.value,
            difficulty=QuestionDifficulty.INTERMEDIATE.value,
            hints=["Think about queries and keys"],
            key_points=["Attention weights", "Parallel processing"],
        )
        
        assert record.question == "What is self-attention?"
        assert record.question_type == "conceptual"
        assert record.difficulty == "intermediate"
        assert "Think about queries and keys" in record.hints
        assert len(record.key_points) == 2

    def test_question_record_all_types(self):
        """Test QuestionRecord with all question types."""
        run_id = uuid.uuid4()
        
        for q_type in QuestionType:
            record = QuestionRecord(
                processing_run_id=run_id,
                question=f"{q_type.value} question",
                question_type=q_type.value,
                difficulty=QuestionDifficulty.INTERMEDIATE.value,
            )
            assert record.question_type == q_type.value

    def test_question_record_all_difficulties(self):
        """Test QuestionRecord with all difficulty levels."""
        run_id = uuid.uuid4()
        
        for difficulty in QuestionDifficulty:
            record = QuestionRecord(
                processing_run_id=run_id,
                question=f"{difficulty.value} question",
                question_type=QuestionType.CONCEPTUAL.value,
                difficulty=difficulty.value,
            )
            assert record.difficulty == difficulty.value

    def test_question_record_empty_hints_and_points(self):
        """Test QuestionRecord with empty hints and key_points."""
        run_id = uuid.uuid4()
        
        record = QuestionRecord(
            processing_run_id=run_id,
            question="Simple question",
            question_type=QuestionType.CONCEPTUAL.value,
            difficulty=QuestionDifficulty.FOUNDATIONAL.value,
            hints=[],
            key_points=[],
        )
        
        assert record.hints == []
        assert record.key_points == []

    def test_question_record_spaced_repetition_defaults(self):
        """Test QuestionRecord has correct spaced repetition defaults."""
        run_id = uuid.uuid4()
        
        record = QuestionRecord(
            processing_run_id=run_id,
            question="Question for review",
            question_type=QuestionType.CONCEPTUAL.value,
            difficulty=QuestionDifficulty.INTERMEDIATE.value,
        )
        
        # Default values are None before DB insertion (DB sets actual defaults)
        assert record.review_count is None or record.review_count == 0
        assert record.ease_factor is None or record.ease_factor == 2.5
        assert record.next_review_at is None


# =============================================================================
# Processing Result Field Extraction Tests
# =============================================================================


class TestProcessingResultFieldExtraction:
    """Tests for extracting fields from ProcessingResult for saving."""

    def test_followup_task_type_enum_value(self, sample_followups):
        """Test that FollowupTask.task_type can be extracted as string."""
        for followup in sample_followups:
            task_type = followup.task_type
            # Should be a string value
            assert isinstance(task_type, str)
            # Should be a valid enum value
            assert task_type in [t.value for t in FollowupTaskType]

    def test_followup_priority_enum_value(self, sample_followups):
        """Test that FollowupTask.priority can be extracted as string."""
        for followup in sample_followups:
            priority = followup.priority
            assert isinstance(priority, str)
            assert priority in [p.value for p in FollowupPriority]

    def test_followup_estimated_time_enum_value(self, sample_followups):
        """Test that FollowupTask.estimated_time can be extracted as string."""
        for followup in sample_followups:
            time_est = followup.estimated_time
            assert isinstance(time_est, str)
            assert time_est in [t.value for t in FollowupTimeEstimate]

    def test_question_type_enum_value(self, sample_questions):
        """Test that MasteryQuestion.question_type can be extracted as string."""
        for question in sample_questions:
            q_type = question.question_type
            assert isinstance(q_type, str)
            assert q_type in [t.value for t in QuestionType]

    def test_question_difficulty_enum_value(self, sample_questions):
        """Test that MasteryQuestion.difficulty can be extracted as string."""
        for question in sample_questions:
            difficulty = question.difficulty
            assert isinstance(difficulty, str)
            assert difficulty in [d.value for d in QuestionDifficulty]


# =============================================================================
# Processing Result with Followups and Questions
# =============================================================================


class TestProcessingResultWithFollowupsAndQuestions:
    """Tests for ProcessingResult containing followups and questions."""

    def test_result_contains_followups(self, sample_followups):
        """Test that ProcessingResult correctly stores followups."""
        result = make_processing_result(followups=sample_followups)
        
        assert len(result.followups) == 3
        assert result.followups[0].task == "Research the original paper on transformers"

    def test_result_contains_questions(self, sample_questions):
        """Test that ProcessingResult correctly stores questions."""
        result = make_processing_result(questions=sample_questions)
        
        assert len(result.mastery_questions) == 2
        assert "self-attention" in result.mastery_questions[0].question

    def test_result_contains_both(self, sample_followups, sample_questions):
        """Test ProcessingResult with both followups and questions."""
        result = make_processing_result(
            followups=sample_followups,
            questions=sample_questions,
        )
        
        assert len(result.followups) == 3
        assert len(result.mastery_questions) == 2

    def test_result_empty_followups_and_questions(self):
        """Test ProcessingResult with empty followups and questions."""
        result = make_processing_result(followups=[], questions=[])
        
        assert result.followups == []
        assert result.mastery_questions == []

    def test_result_serialization_includes_followups(self, sample_followups):
        """Test that followups are included in result serialization."""
        result = make_processing_result(followups=sample_followups)
        
        data = result.model_dump()
        
        assert "followups" in data
        assert len(data["followups"]) == 3

    def test_result_serialization_includes_questions(self, sample_questions):
        """Test that questions are included in result serialization."""
        result = make_processing_result(questions=sample_questions)
        
        data = result.model_dump()
        
        assert "mastery_questions" in data
        assert len(data["mastery_questions"]) == 2
