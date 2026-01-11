"""
Learning System Services

Services for the FSRS-based spaced repetition system and
exercise-based active learning features.

Modules:
- fsrs: FSRS algorithm implementation wrapper
- spaced_rep_service: Card management and review processing
- exercise_generator: LLM-powered exercise generation
- evaluator: Response evaluation with LLM feedback
- code_sandbox: Docker-based code execution sandbox
- session_service: Practice session orchestration
- session_budget: Time budget management for sessions
- mastery_service: Mastery tracking and analytics

Usage:
    from app.services.learning import (
        SpacedRepService,
        ExerciseGenerator,
        ResponseEvaluator,
        SessionService,
        SessionTimeBudget,
        MasteryService,
    )
"""

from app.services.learning.fsrs import (
    FSRSScheduler,
    CardState as FSRSCardState,
    create_scheduler,
    get_review_forecast,
)
from app.services.learning.spaced_rep_service import SpacedRepService
from app.services.learning.exercise_generator import ExerciseGenerator
from app.services.learning.evaluator import ResponseEvaluator
from app.services.learning.code_sandbox import CodeSandbox, get_code_sandbox
from app.services.learning.session_service import SessionService
from app.services.learning.session_budget import (
    SessionTimeBudget,
    resolve_content_mode,
    resolve_exercise_source,
    resolve_card_source,
)
from app.services.learning.mastery_service import MasteryService

__all__ = [
    # FSRS
    "FSRSScheduler",
    "FSRSCardState",
    "create_scheduler",
    "get_review_forecast",
    # Services
    "SpacedRepService",
    "ExerciseGenerator",
    "ResponseEvaluator",
    "CodeSandbox",
    "get_code_sandbox",
    "SessionService",
    "SessionTimeBudget",
    "resolve_content_mode",
    "resolve_exercise_source",
    "resolve_card_source",
    "MasteryService",
]
