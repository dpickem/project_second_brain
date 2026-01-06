# Learning System Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: January 2025  
> **Target Phases**: Phase 6-8 (Weeks 18-29) — Backend + Frontend  
> **Design Doc**: `design_docs/05_learning_system.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Learning System, which transforms passive content consumption into active learning through spaced repetition, retrieval practice, and adaptive exercises. The Learning System is the culmination of the Second Brain project—where knowledge is not just stored, but actively reinforced and mastered.

### Why This Phase Matters

The Learning System implements research-backed techniques from cognitive science:

| Research Foundation | Implementation | User Benefit |
|---------------------|----------------|--------------|
| **FSRS Algorithm** | Modern spaced repetition scheduler | 90% retention with minimal review time |
| **Deliberate Practice** | Adaptive difficulty, immediate feedback | Learning at the edge of ability |
| **Desirable Difficulties** | Free recall, interleaving, generation | Stronger long-term retention |
| **Self-Explanation** | Teach-back exercises, explain prompts | Deeper understanding |
| **Worked Examples** | Scaffolded problems for novices | Reduced cognitive load |

### System Architecture Overview

```text
LEARNING SYSTEM ARCHITECTURE
============================

┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PracticeView │  │  ReviewQueue │  │  Analytics   │  │ WeakSpots    │    │
│  │ - Exercises  │  │  - Due Cards │  │  - Mastery   │  │ - Topics     │    │
│  │ - Feedback   │  │  - Ratings   │  │  - Trends    │  │ - Recommend  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND API (FastAPI)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/practice/*     /api/review/*      /api/analytics/*                    │
│  - /session          - /due             - /mastery                          │
│  - /submit           - /rate            - /weak-spots                       │
│  - /exercise         - /cards           - /learning-curve                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   FSRS Scheduler    │ │  Exercise Generator │ │   Code Evaluator    │
│   - CardState       │ │  - LLM Prompts      │ │   - Docker Sandbox  │
│   - Scheduling      │ │  - Adaptive         │ │   - Test Runner     │
│   - Stability       │ │  - Evaluation       │ │   - LLM Review      │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL                    Redis                   Neo4j                │
│  - spaced_rep_cards           - Session cache         - Concept relations  │
│  - practice_sessions          - Exercise queue        - Prerequisite paths │
│  - practice_attempts          - Rate limiting         - Topic hierarchy    │
│  - mastery_snapshots                                                        │
│  - exercises                                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| FSRS spaced repetition algorithm | Mobile-native app |
| Exercise generation (6+ types) | Real-time multiplayer |
| Code exercise evaluation (Docker sandbox) | GPU-accelerated code execution |
| Practice session management | Voice-based practice |
| Mastery tracking & analytics | Gamification (leaderboards, badges) |
| Weak spot detection | Social features |
| LLM-powered feedback | External LMS integration |

---

## 2. Prerequisites

### 2.1 Prior Phases Required

| Phase | Component | Why Required |
|-------|-----------|--------------|
| **Phase 1** | PostgreSQL + existing tables | Base data models, `Content`, `Tag` tables |
| **Phase 1** | Redis | Session caching, exercise queues |
| **Phase 3** | LLM Client (`llm_client.py`) | Exercise generation, response evaluation |
| **Phase 4** | Neo4j Knowledge Graph | Concept relationships for learning paths |

### 2.2 Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 24+ | Code sandbox execution |
| Python | 3.11+ | Backend services |
| Node.js | 18+ | Frontend build |
| PostgreSQL | 16 | Learning records |
| Redis | 7 | Session & queue management |
| Neo4j | 5 | Knowledge graph queries |

### 2.3 New Dependencies

```txt
# Add to backend/requirements.txt

# FSRS Algorithm
fsrs>=3.0.0                    # Free Spaced Repetition Scheduler library
```

**Already Available** (no changes needed):
- `docker>=7.0.0` — Docker container management
- `apscheduler>=3.10.0` — Background job scheduling
- `tenacity>=8.2.3` — Retry logic with exponential backoff

**Why FSRS:**

| Package | Why This One | Alternatives Considered |
|---------|--------------|------------------------|
| `fsrs` | Reference implementation of FSRS-4.5, well-tested, actively maintained | Custom implementation (more work, bug-prone), `sm-2` (outdated algorithm) |

### 2.4 Environment Variables

```bash
# Add to .env file

# Docker Sandbox Configuration
SANDBOX_TIMEOUT_SECONDS=10              # Max execution time per test
SANDBOX_MEMORY_LIMIT=128m               # Memory limit per container
SANDBOX_CPU_QUOTA=50000                 # CPU quota (50% of one core)
SANDBOX_ENABLED=true                    # Enable/disable code execution

# Learning System Configuration
FSRS_DESIRED_RETENTION=0.9              # Target 90% recall probability
PRACTICE_SESSION_DEFAULT_MINUTES=15     # Default session length
MASTERY_SNAPSHOT_HOUR=3                 # Hour (UTC) to run daily snapshots
WEAK_SPOT_THRESHOLD=0.6                 # Mastery below this = weak spot

# Exercise Generation
EXERCISE_LLM_MODEL=gpt-4-turbo          # Model for exercise generation
FEEDBACK_LLM_MODEL=gpt-3.5-turbo        # Model for response feedback (cheaper)
```

---

## 3. Implementation Phases

### Phase 6A: Database Schema Extensions (Days 1-3)

#### Task 6A.1: Extended Spaced Repetition Card Model

**Purpose**: Upgrade the existing `SpacedRepCard` model to support the full FSRS algorithm with additional metadata for exercise types and code cards.

**Why FSRS Over SM-2?**

| Feature | SM-2 (Current) | FSRS (Target) |
|---------|----------------|---------------|
| Memory model | Simple exponential | Forgetting curve based on stability |
| Difficulty | Static 2.5 factor | Dynamic, content-specific |
| Retention prediction | None | Precise retention probability |
| Optimization | Fixed parameters | Personalized from review history |
| Research | 1987 | 2022, validated against Anki data |

**FSRS Key Concepts:**

```text
FSRS MEMORY MODEL
=================

STABILITY (S): Days until memory strength decays to 90% recall probability
- New card: S = 0.4 to 5.8 (based on initial rating)
- After review: S increases (success) or decreases (failure)
- Higher S → longer intervals between reviews

DIFFICULTY (D): Inherent difficulty of the card (0-1)
- Easy cards: D ≈ 0.1-0.3
- Hard cards: D ≈ 0.7-0.9
- Updated based on review performance patterns

RETRIEVABILITY (R): Current recall probability
- R = (1 + interval_days / (9 * S))^(-1)
- When R = desired_retention (0.9), schedule review

Review Timeline Example:
┌─────────────────────────────────────────────────────────────────────────┐
│ Day 0: Learn card (S=1.0)                                               │
│ Day 1: Review - Good (S=3.2)    R was 0.90                              │
│ Day 3: Review - Good (S=8.5)    R was 0.91                              │
│ Day 10: Review - Hard (S=12.0)  R was 0.88                              │
│ Day 24: Review - Good (S=28.0)  R was 0.90                              │
│ Day 60: Next review scheduled   R will be ~0.90                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Migration File:** `backend/alembic/versions/007_learning_system_schema.py`

**Schema Changes:**

| Table | Change | Columns |
|-------|--------|---------|
| `spaced_rep_cards` | ADD columns | `stability`, `difficulty`, `state`, `lapses`, `scheduled_days`, `language`, `starter_code`, `solution_code`, `test_cases`, `tags`, `concept_id` |
| `exercises` | CREATE table | `exercise_uuid`, `exercise_type`, `topic`, `difficulty`, `prompt`, `hints`, `expected_key_points`, `worked_example`, `follow_up_problem`, `language`, `starter_code`, `solution_code`, `test_cases`, `buggy_code`, `source_content_ids`, `estimated_time_minutes`, `tags`, timestamps |
| `exercise_attempts` | CREATE table | `session_id` (FK), `exercise_id` (FK), `response`, `response_code`, `score`, `is_correct`, `feedback`, `covered_points`, `missing_points`, `misconceptions`, `tests_passed`, `tests_total`, `test_results`, `execution_error`, `confidence_before`, `confidence_after`, `time_spent_seconds`, `attempted_at` |
| `mastery_snapshots` | ADD columns | `topic_path`, `practice_count`, `success_rate`, `trend`, `last_practiced`, `retention_estimate`, `days_since_review` |
| `practice_sessions` | ADD columns | `topics_covered`, `exercise_count`, `average_score`, `duration_minutes` |

**Indexes to Create:**
- `ix_cards_due_date_state` on `spaced_rep_cards(due_date, state)`
- `ix_cards_concept` on `spaced_rep_cards(concept_id)`
- `ix_exercises_topic` on `exercises(topic)`
- `ix_exercises_type_difficulty` on `exercises(exercise_type, difficulty)`
- `ix_exercise_attempts_session` on `exercise_attempts(session_id)`
- `ix_exercise_attempts_exercise` on `exercise_attempts(exercise_id)`
- `ix_mastery_topic` on `mastery_snapshots(topic_path)`
- `ix_mastery_date_topic` on `mastery_snapshots(snapshot_date, topic_path)`

**Deliverables:**
- [ ] Migration script for learning system schema
- [ ] FSRS columns added to spaced_rep_cards
- [ ] Exercises table created
- [ ] Exercise attempts table created
- [ ] Enhanced mastery tracking columns
- [ ] All indexes created

**Estimated Time:** 3 hours

---

#### Task 6A.2: SQLAlchemy Model Updates

**Purpose**: Create SQLAlchemy models for the new tables and extend existing models.

**File:** `backend/app/db/models_learning.py`

**Enums to Define:**

| Enum | Values | Purpose |
|------|--------|---------|
| `CardState` | `new`, `learning`, `review`, `relearning` | FSRS state machine |
| `ExerciseType` | `free_recall`, `self_explain`, `worked_example`, `application`, `compare_contrast`, `teach_back`, `debug`, `code_implement`, `code_complete`, `code_debug`, `code_refactor`, `code_explain` | Exercise categorization |
| `ExerciseDifficulty` | `foundational`, `intermediate`, `advanced` | Mastery-aligned difficulty |

**Models to Create:**

| Model | Key Fields | Relationships |
|-------|------------|---------------|
| `Exercise` | `exercise_uuid`, `exercise_type`, `topic`, `difficulty`, `prompt`, `hints[]`, `expected_key_points[]`, `worked_example`, `starter_code`, `solution_code`, `test_cases[]` | `attempts` → ExerciseAttempt |
| `ExerciseAttempt` | `session_id`, `exercise_id`, `response`, `score`, `is_correct`, `feedback`, `covered_points[]`, `missing_points[]`, `confidence_before/after`, `time_spent_seconds` | `session` → PracticeSession, `exercise` → Exercise |

**Deliverables:**
- [ ] Enum classes for states/types/difficulties
- [ ] Exercise model with all fields
- [ ] ExerciseAttempt model with evaluation fields
- [ ] Relationship definitions

**Estimated Time:** 2 hours

---

#### Task 6A.3: Pydantic API Models

**Purpose**: Define request/response schemas for the Learning System API.

**File:** `backend/app/models/learning.py`

**Enums:**

| Enum | Values | Purpose |
|------|--------|---------|
| `Rating` | `AGAIN=1`, `HARD=2`, `GOOD=3`, `EASY=4` | FSRS review ratings |
| `ExerciseTypeEnum` | (mirrors SQLAlchemy enum) | Exercise type filtering |
| `DifficultyEnum` | `foundational`, `intermediate`, `advanced` | Difficulty levels |
| `CardStateEnum` | `new`, `learning`, `review`, `relearning` | FSRS states |

**Spaced Repetition Models:**

| Model | Key Fields | Purpose |
|-------|------------|---------|
| `CardBase` | `card_type`, `front`, `back`, `hints[]`, `tags[]` | Base card fields |
| `CardCreate` | extends CardBase + `content_id`, `concept_id`, `language`, `starter_code`, `solution_code`, `test_cases[]` | Create new card |
| `CardResponse` | extends CardBase + FSRS state (`state`, `stability`, `difficulty`, `due_date`) + stats (`repetitions`, `lapses`) | API response |
| `CardReviewRequest` | `card_id`, `rating`, `response?`, `time_spent_seconds?` | Submit review |
| `CardReviewResponse` | `card_id`, `new_state`, `new_stability`, `new_difficulty`, `next_due_date`, `scheduled_days` | Review result |
| `DueCardsResponse` | `cards[]`, `total_due`, `review_forecast{}` | Due cards list |

**Exercise Models:**

| Model | Key Fields | Purpose |
|-------|------------|---------|
| `ExerciseBase` | `exercise_type`, `topic`, `difficulty`, `prompt`, `hints[]`, `expected_key_points[]` | Base fields |
| `ExerciseCreate` | extends ExerciseBase + `worked_example`, `starter_code`, `solution_code`, `test_cases[]`, `buggy_code` | Create exercise |
| `ExerciseResponse` | extends ExerciseBase + `id`, `exercise_uuid` (hides solution) | API response |
| `ExerciseWithSolution` | extends ExerciseResponse + `solution_code`, `test_cases[]` | Post-attempt response |
| `ExerciseGenerateRequest` | `topic`, `exercise_type?`, `difficulty?`, `language?` | Generation request |
| `AttemptSubmitRequest` | `exercise_id`, `response?`, `response_code?`, `confidence_before?`, `time_spent_seconds?` | Submit attempt |
| `AttemptEvaluationResponse` | `score`, `is_correct`, `feedback`, `covered_points[]`, `missing_points[]`, `misconceptions[]`, `test_results[]?` | Evaluation result |

**Session Models:**

| Model | Key Fields | Purpose |
|-------|------------|---------|
| `SessionCreateRequest` | `duration_minutes`, `topic_filter?`, `session_type` | Create session |
| `SessionItem` | `item_type`, `card?`, `exercise?`, `estimated_minutes` | Session item |
| `SessionResponse` | `session_id`, `items[]`, `estimated_duration_minutes`, `topics_covered[]` | Session with items |
| `SessionSummary` | `cards_reviewed`, `exercises_completed`, `correct_count`, `average_score`, `mastery_changes{}` | Post-session summary |

**Analytics Models:**

| Model | Key Fields | Purpose |
|-------|------------|---------|
| `MasteryState` | `topic_path`, `mastery_score`, `confidence_avg`, `practice_count`, `success_rate`, `trend` | Topic mastery |
| `WeakSpot` | `topic`, `mastery_score`, `success_rate`, `trend`, `recommendation`, `suggested_exercises[]` | Weak spot info |
| `MasteryOverview` | `overall_mastery`, `topics[]`, `total_cards`, `cards_mastered/learning/new`, `streak_days` | Overall stats |
| `LearningCurveResponse` | `topic?`, `data_points[]`, `trend`, `projected_mastery_30d` | Learning curve data |

**Deliverables:**
- [ ] All Pydantic models for API contracts
- [ ] Proper validation with Field constraints
- [ ] Enum definitions for type safety

**Estimated Time:** 2 hours

---

### Phase 6B: FSRS Algorithm Implementation (Days 4-7)

#### Task 6B.1: FSRS Scheduler Core

**Purpose**: Implement the Free Spaced Repetition Scheduler algorithm that calculates optimal review intervals.

**FSRS Algorithm Deep Dive:**

```text
FSRS-4.5 ALGORITHM OVERVIEW
===========================

The FSRS algorithm models memory as having two components:

1. STABILITY (S): How resistant the memory is to forgetting
   - Measured in days until retention drops to 90%
   - Increases with successful reviews
   - Decreases (resets) on lapses

2. DIFFICULTY (D): Inherent difficulty of the material
   - Range: 0 (trivial) to 1 (very hard)
   - Adjusts based on review performance patterns
   - Affects how quickly stability grows

KEY FORMULAS:

Initial Stability (first review):
  S₀ = w[rating-1]  where w[0..3] = [0.4, 0.6, 2.4, 5.8]

Stability After Success:
  S' = S × (1 + e^w[8] × (11 - D×10) × S^(-w[9]) × (e^((1-R)×w[10]) - 1))

Stability After Failure (Lapse):
  S' = w[11] × D^(-w[12]) × (S+1)^w[13] × e^((1-R)×w[14])

Difficulty Update:
  D' = D + w[6] × (rating - 3) / 3

Interval Calculation:
  interval = S × ln(desired_retention) / ln(0.9)

Where:
  - w[0..16] are the 17 FSRS parameters (defaults provided)
  - R is the current retrievability (recall probability)
  - rating is 1-4 (Again, Hard, Good, Easy)
```

**File:** `backend/app/services/learning/fsrs.py`

**Recommendation:** Use the `fsrs` pip package (reference implementation) rather than implementing from scratch. Wrap it in a thin service layer.

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `Rating` enum | AGAIN=1, HARD=2, GOOD=3, EASY=4 |
| `State` enum | NEW, LEARNING, REVIEW, RELEARNING |
| `FSRSParameters` | 17 weight parameters + retention target (0.9) + max interval (365 days) |
| `CardState` dataclass | state, difficulty, stability, due, last_review, reps, lapses |

**Core Algorithm (pseudo-code):**

```
CLASS FSRSScheduler:
    
    METHOD review(card, rating) -> (new_card, log):
        elapsed_days = days_since(card.last_review)
        
        IF card.state == NEW:
            difficulty = init_difficulty(rating)  # AGAIN->0.7, EASY->0.3
            stability = params.w[rating - 1]      # Initial stability from params
            
            IF rating == AGAIN or HARD:
                new_state = LEARNING, interval = 1
            ELIF rating == GOOD:
                new_state = LEARNING, interval = calculate_interval(stability)
            ELSE:  # EASY
                new_state = REVIEW, interval = calculate_interval(stability)
        
        ELIF card.state == LEARNING or RELEARNING:
            difficulty = update_difficulty(card.difficulty, rating)
            
            IF rating == AGAIN:
                stability = params.w[0], new_state = LEARNING, interval = 1
                IF was RELEARNING: lapses += 1
            ELIF rating == HARD:
                stability = next_stability(...)
                new_state = LEARNING, interval = calculate_interval(stability) / 2
            ELIF rating == GOOD:
                stability = next_stability(...)
                new_state = REVIEW, interval = calculate_interval(stability)
            ELSE:  # EASY
                stability = next_stability(...)
                new_state = REVIEW, interval = calculate_interval(stability) * easy_bonus
        
        ELIF card.state == REVIEW:
            difficulty = update_difficulty(card.difficulty, rating)
            
            IF rating == AGAIN:
                stability = stability_after_fail(...)
                new_state = RELEARNING, interval = 1, lapses += 1
            ELSE:
                stability = next_stability(...)
                new_state = REVIEW
                interval = calculate_interval(stability) * modifier(rating)
        
        RETURN updated_card, review_log
    
    METHOD next_stability(S, D, rating, elapsed):
        R = retention(S, elapsed)  # Current recall probability
        # FSRS formula: S' = S * (1 + e^w8 * (11-D*10) * S^-w9 * (e^((1-R)*w10) - 1))
        RETURN new_stability * rating_modifier
    
    METHOD retention(stability, elapsed):
        RETURN (1 + elapsed / (9 * stability))^-1
    
    METHOD calculate_interval(stability):
        # Days until retention drops to target (default 90%)
        RETURN stability * ln(target_retention) / ln(0.9)
```

**Helper Functions:**
- `create_scheduler(retention, max_interval)` → configured FSRSScheduler
- `get_due_cards_count(cards)` → {overdue, today, tomorrow, this_week, later}

**Deliverables:**
- [ ] FSRSScheduler class with full algorithm
- [ ] CardState dataclass for persistence
- [ ] All state transitions implemented
- [ ] Difficulty and stability calculations
- [ ] Interval calculation with retention targeting
- [ ] Unit tests for all edge cases

**Estimated Time:** 6 hours

---

#### Task 6B.2: FSRS Service Layer

**Purpose**: Create a service layer that integrates FSRS with the database and provides business logic.

**File:** `backend/app/services/learning/spaced_rep_service.py`

**Class:** `SpacedRepService`

```
CLASS SpacedRepService:
    INIT(db: AsyncSession):
        self.db = db
        self.scheduler = create_scheduler(retention=0.9, max_interval=365)
    
    METHOD create_card(card_data) -> SpacedRepCard:
        # Create card with initial FSRS state (new, difficulty=0.3, stability=0, due=now)
        # Persist to database
        RETURN card
    
    METHOD get_due_cards(limit=50, topic_filter=None) -> DueCardsResponse:
        # Query: WHERE due_date <= now ORDER BY due_date ASC LIMIT limit
        # Optional: filter by topic in tags
        # Also generate forecast for today/tomorrow/this_week
        RETURN {cards, total_due, review_forecast}
    
    METHOD review_card(request) -> CardReviewResponse:
        1. Load card from DB
        2. Convert to FSRS CardState dataclass
        3. Run scheduler.review(state, rating) -> get new state
        4. Update card in DB with new state/stability/difficulty/due_date
        5. Increment total_reviews, correct_reviews if rating != AGAIN
        RETURN {card_id, new_state, new_stability, new_difficulty, next_due_date, scheduled_days}
    
    METHOD get_card_stats() -> dict:
        # GROUP BY state to get counts (new, learning, review, relearning)
        # Calculate AVG(stability), AVG(difficulty) for review cards
        RETURN {total_cards, new_cards, learning_cards, review_cards, avg_stability, avg_difficulty}
    
    METHOD _get_review_forecast() -> dict:
        # Count cards due today, tomorrow, this_week
        RETURN {today, tomorrow, this_week}
```

**Deliverables:**
- [ ] SpacedRepService class
- [ ] Card CRUD operations
- [ ] Review processing with FSRS
- [ ] Due card queries
- [ ] Statistics methods

**Estimated Time:** 4 hours

---

### Phase 6C: Exercise Generation System (Days 8-14)

#### Task 6C.1: Exercise Generator Service

**Purpose**: Create an LLM-powered exercise generation service that creates adaptive exercises based on content and mastery level.

**Exercise Type Selection Logic:**

```text
EXERCISE TYPE SELECTION
=======================

Based on mastery level and learning science principles:

MASTERY < 0.3 (Novice)
├─► WORKED_EXAMPLE
│   - Show step-by-step solution first
│   - Then present similar problem
│   - Reduces cognitive load (Van Gog et al.)
│
└─► CODE_COMPLETE (for code topics)
    - Fill in blanks, not write from scratch
    - Scaffolded learning

MASTERY 0.3 - 0.7 (Intermediate)
├─► FREE_RECALL
│   - "Explain X without looking at notes"
│   - Strengthens retrieval pathways (Bjork)
│
├─► SELF_EXPLAIN  
│   - "Why does X work this way?"
│   - Builds mental models (Chi et al.)
│
├─► CODE_IMPLEMENT
│   - Write code from scratch
│   - Apply understanding
│
└─► DEBUG
    - Find errors in code/logic
    - Tests deep understanding

MASTERY > 0.7 (Advanced)
├─► APPLICATION
│   - Apply to novel situations
│   - Transfer learning
│
├─► TEACH_BACK
│   - Explain as if teaching someone
│   - Feynman technique
│
├─► CODE_REFACTOR
│   - Improve existing code
│   - Requires optimization thinking
│
└─► COMPARE_CONTRAST
    - Relate to other concepts
    - Integration of knowledge
```

**File:** `backend/app/services/learning/exercise_generator.py`

**Prompt Templates:** Define LLM prompt templates for each exercise type:

| Exercise Type | Prompt Purpose | Expected JSON Output |
|---------------|----------------|---------------------|
| `FREE_RECALL` | Explain concept from memory | `{prompt, hints[], expected_key_points[], estimated_time}` |
| `SELF_EXPLAIN` | Explain WHY/HOW/WHAT-IF | Same as above |
| `WORKED_EXAMPLE` | Step-by-step solution + follow-up | `{worked_example, follow_up_problem, hints[], expected_key_points[]}` |
| `CODE_IMPLEMENT` | Implement function | `{prompt, starter_code, solution_code, test_cases[], hints[]}` |
| `CODE_DEBUG` | Find and fix bugs | `{prompt, buggy_code, solution_code, bugs[], test_cases[]}` |
| `TEACH_BACK` | Explain to someone else (Feynman) | `{prompt, hints[], expected_key_points[]}` |

**Class:** `ExerciseGenerator`

```
CLASS ExerciseGenerator:
    INIT(llm_client, db):
        self.llm = llm_client
        self.db = db
    
    METHOD generate_exercise(request, mastery_level, previous_results) -> Exercise:
        1. Select difficulty based on mastery:
           - mastery < 0.3 → FOUNDATIONAL
           - mastery 0.3-0.7 → INTERMEDIATE
           - mastery > 0.7 → ADVANCED
        
        2. Select exercise type if not specified:
           - Novice (mastery < 0.3): WORKED_EXAMPLE or CODE_COMPLETE
           - Intermediate: FREE_RECALL or CODE_IMPLEMENT/DEBUG
           - Advanced: TEACH_BACK or CODE_REFACTOR
        
        3. Build prompt from template with {topic, mastery_level, previous_summary, language}
        4. Call LLM with JSON response format
        5. Parse response and create Exercise model
        6. Persist to database
        RETURN exercise
    
    METHOD _select_exercise_type(mastery, is_code) -> ExerciseTypeEnum:
        # Map mastery level to appropriate exercise type
        # Code topics get code-specific exercises
    
    METHOD _get_topic_context(topic) -> str:
        # Query Neo4j for related concepts (future)
```

**Deliverables:**
- [ ] ExerciseGenerator class
- [ ] Prompt templates for all exercise types
- [ ] Adaptive difficulty selection
- [ ] Adaptive exercise type selection
- [ ] LLM integration for generation

**Estimated Time:** 8 hours

---

#### Task 6C.2: Response Evaluation Service

**Purpose**: Evaluate learner responses to exercises using LLM and provide detailed feedback.

**File:** `backend/app/services/learning/evaluator.py`

**Evaluation Prompt Template:** LLM prompt that provides exercise, expected key points, and learner response, expecting JSON with:
- `covered_points[]` - points covered with evidence quotes
- `missing_points[]` - points not addressed
- `misconceptions[]` - identified errors with corrections
- `overall_score` - 1-5 scale
- `specific_feedback` - personalized feedback
- `suggested_review[]` - topics to review

**Class:** `ResponseEvaluator`

```
CLASS ResponseEvaluator:
    INIT(llm_client, db):
        self.llm = llm_client
        self.db = db
    
    METHOD evaluate_response(exercise, response, confidence_before) -> AttemptEvaluationResponse:
        1. Build evaluation prompt with exercise.prompt, expected_key_points, response
        2. Call LLM with JSON response format
        3. Parse result: score = overall_score / 5.0 (normalize to 0-1)
        4. Determine correctness: is_correct = score >= 0.6
        5. Create and persist ExerciseAttempt record
        6. Build ExerciseWithSolution (reveals solution after attempt)
        RETURN {attempt_id, score, is_correct, feedback, covered_points, missing_points, 
                misconceptions, suggested_review, exercise_with_solution}
```

**Deliverables:**
- [ ] ResponseEvaluator class
- [ ] LLM evaluation prompt
- [ ] Feedback generation
- [ ] Attempt recording
- [ ] Solution reveal logic

**Estimated Time:** 4 hours

---

### Phase 6D: Code Evaluation Sandbox (Days 15-19)

#### Task 6D.1: Docker Sandbox Manager

**Purpose**: Create a secure Docker-based sandbox for executing learner-submitted code with strict resource limits.

**Security Requirements:**

```text
SANDBOX SECURITY MODEL
======================

THREATS TO MITIGATE:
1. Resource exhaustion (CPU, memory, disk)
2. Network access (data exfiltration, attacks)
3. File system access (read secrets, write malware)
4. Process spawning (fork bombs)
5. Long-running processes (hang)

MITIGATIONS:
┌─────────────────────────────────────────────────────────────────────────┐
│ CONTAINER LIMITS                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ Memory:      128MB hard limit, no swap                                  │
│ CPU:         50% of one core (cpu_quota=50000)                          │
│ Network:     Completely disabled                                         │
│ Filesystem:  Read-only except /tmp (10MB max)                           │
│ Processes:   Max 50 (prevents fork bombs)                               │
│ Time:        10 second timeout, killed after                            │
│ User:        Non-root (sandbox user)                                    │
└─────────────────────────────────────────────────────────────────────────┘

EXECUTION FLOW:
1. Create temp directory with code file
2. Start container with strict limits
3. Mount code as read-only
4. Execute with timeout
5. Capture stdout/stderr
6. Kill container
7. Clean up temp files
```

**File:** `backend/app/services/learning/code_sandbox.py`

**Dataclasses:**
- `ExecutionResult`: success, stdout, stderr, exit_code, timed_out, error
- `TestResult`: test_index, passed, input_value, expected, actual, error

**Language Support:**

| Language | Image | Extension | Command |
|----------|-------|-----------|---------|
| python | python:3.11-slim | .py | python3 |
| pytorch | pytorch/pytorch:2.1.0-cpu | .py | python3 |
| javascript | node:20-alpine | .js | node |
| typescript | node:20-alpine | .ts | npx ts-node |

**Security Limits:** 128MB memory (no swap), 50% CPU, network disabled, read-only FS, 50 max PIDs, 10s timeout

**Class:** `CodeSandbox`

```
CLASS CodeSandbox:
    INIT():
        self.docker_client = docker.from_env()
        self.timeout = settings.SANDBOX_TIMEOUT_SECONDS
        self.enabled = settings.SANDBOX_ENABLED
    
    METHOD execute_code(code, language, timeout) -> ExecutionResult:
        IF not enabled: RETURN error result
        
        1. Create temp directory with code file
        2. Get language config (image, extension, command)
        3. Run container with strict limits
        4. Wait for completion with timeout
        5. Capture stdout/stderr
        6. Clean up temp directory
        RETURN {success, stdout, stderr, exit_code, timed_out}
    
    METHOD run_tests(code, test_cases, language) -> List[TestResult]:
        FOR each test_case:
            1. Create test wrapper (appends test harness to code)
            2. Execute code with test input
            3. Compare stdout with expected output
            4. Record pass/fail and any errors
        RETURN results[]
    
    METHOD _run_container(image, command, code_dir, timeout) -> ExecutionResult:
        1. Create container with security limits
        2. Mount code directory as read-only
        3. Run with timeout using asyncio.wait_for
        4. Kill container on timeout
        5. Collect logs
        6. Remove container
        RETURN result
    
    METHOD _create_test_wrapper(code, test, language) -> str:
        # Append test harness that calls solution() and prints result
```

**Deliverables:**
- [ ] CodeSandbox class
- [ ] Docker container management
- [ ] Security limits implementation
- [ ] Test runner with comparison
- [ ] Language-specific handlers
- [ ] Timeout handling

**Estimated Time:** 8 hours

---

### Phase 7A: Practice Session API (Days 20-25)

#### Task 7A.1: Practice Session Service

**Purpose**: Create the service that orchestrates practice sessions, combining spaced repetition cards and exercises.

**File:** `backend/app/services/learning/session_service.py`

**Session Composition (Learning Science Principles):**
- 40% due spaced rep cards (review consolidates memory)
- 30% weak spot exercises (deliberate practice)
- 30% new/interleaved content (improves transfer)

**Class:** `SessionService`

```
CLASS SessionService:
    TIME_ALLOCATION = {spaced_rep: 0.4, weak_spots: 0.3, new_content: 0.3}
    
    INIT(db, spaced_rep_service, exercise_generator, mastery_service):
        # Inject dependencies
    
    METHOD create_session(request) -> SessionResponse:
        duration = request.duration_minutes
        items = []
        topics = []
        
        # 1. Get due spaced rep cards (40% of time, ~2 min per card)
        due_cards = spaced_rep.get_due_cards(limit=duration*0.4//2)
        FOR each card: add SessionItem(type="card", card=card)
        
        # 2. Generate weak spot exercise (30% of time)
        weak_spots = mastery.get_weak_spots(limit=3)
        IF weak_spots:
            exercise = exercise_gen.generate_exercise(topic=weak_spots[0].topic)
            add SessionItem(type="exercise", exercise=exercise)
        
        # 3. New content exercise (30% of time)
        IF topic_filter:
            mastery_level = mastery.get_mastery_state(topic).score
            exercise = exercise_gen.generate_exercise(topic, mastery_level)
            add SessionItem(type="exercise", exercise=exercise)
        
        # Interleave (worked examples first, then shuffle rest)
        items = _interleave_items(items)
        
        # Persist session record
        RETURN {session_id, items, estimated_duration, topics_covered}
    
    METHOD end_session(session_id) -> SessionSummary:
        1. Update session.ended_at
        2. Calculate duration and average score
        3. Get mastery changes per topic
        RETURN summary stats
    
    METHOD _interleave_items(items) -> List[SessionItem]:
        # Keep worked examples at start (for novices)
        # Shuffle remaining items for interleaving benefit
```

**Deliverables:**
- [ ] SessionService class
- [ ] Session creation with balanced content
- [ ] Interleaving implementation
- [ ] Session summary calculation
- [ ] Topic coverage tracking

**Estimated Time:** 6 hours

---

### Phase 8A: Mastery Tracking (Days 26-35)

#### Task 8A.1: Mastery Service

**Purpose**: Track and calculate mastery scores per topic based on practice performance and spaced rep card states.

**File:** `backend/app/services/learning/mastery_service.py`

**Mastery Calculation Formula:**
- 60% from success rate (correct_reviews / total_reviews)
- 40% from average stability (normalized: avg_stability / 30 days)

**Weak Spot Detection Criteria:**
- Mastery score < 0.6 threshold
- Declining trend (delta < -0.05 from previous snapshot)
- Many days since practice

**Class:** `MasteryService`

```
CLASS MasteryService:
    WEAK_SPOT_THRESHOLD = 0.6
    MIN_ATTEMPTS_FOR_MASTERY = 3
    
    METHOD get_mastery_state(topic) -> MasteryState:
        1. Check for recent snapshot (within 1 day)
        2. IF no snapshot or stale: _calculate_mastery(topic)
        RETURN {topic_path, mastery_score, practice_count, success_rate, trend, ...}
    
    METHOD get_weak_spots(limit=10) -> List[WeakSpot]:
        # Query snapshots from last 7 days WHERE:
        #   - practice_count >= 3
        #   - mastery_score < 0.6
        # ORDER BY: declining trend first, then lowest mastery
        FOR each snapshot:
            recommendation = _generate_recommendation(snapshot)
        RETURN weak_spots[]
    
    METHOD get_overview() -> MasteryOverview:
        # Aggregate card stats: total, mastered (stability>=21), learning, new
        # Calculate average mastery across all topics
        RETURN {overall_mastery, topics[], card_counts, streak_days, practice_time}
    
    METHOD take_daily_snapshot() -> int:
        # Called by scheduler at midnight
        # Get all unique topics from card tags
        FOR each topic:
            state = _calculate_mastery(topic)
            persist MasterySnapshot
        RETURN count
    
    METHOD _calculate_mastery(topic) -> MasteryState:
        1. Get all cards with this topic in tags
        2. IF total_reviews < 3: RETURN preliminary state
        3. success_rate = correct_reviews / total_reviews
        4. stability_factor = min(1.0, avg_stability / 30)
        5. mastery_score = (success_rate * 0.6) + (stability_factor * 0.4)
        6. Compare to previous snapshot for trend:
           - delta > 0.05 → "improving"
           - delta < -0.05 → "declining"
           - else → "stable"
        RETURN mastery_state
    
    METHOD _generate_recommendation(snapshot) -> str:
        # Prioritize: declining → low success rate → insufficient practice → routine review
```

**Deliverables:**
- [ ] MasteryService class
- [ ] Mastery calculation algorithm
- [ ] Weak spot detection
- [ ] Daily snapshot job
- [ ] Trend analysis
- [ ] Overview statistics

**Estimated Time:** 8 hours

---

### Phase 7B: Practice Session Frontend (Days 26-32)

The Practice Session UI is the primary interface for active learning—where users engage with exercises, submit responses, and receive immediate feedback.

#### Task 7B.1: Practice Session Core Components

**Directory:** `frontend/src/components/practice/`

| Component | Props | Purpose |
|-----------|-------|---------|
| `PracticeSession` | `topicId?`, `sessionLength`, `onComplete` | Main orchestrator - manages session state, current exercise index, feedback display |
| `ExerciseCard` | `exercise` | Displays exercise with type badge, difficulty, prompt, context, code snippet, hints |
| `SessionProgress` | `current`, `total`, `correctCount` | Progress bar and statistics |
| `SessionComplete` | `sessionId`, `onComplete` | Summary view after session ends |

**State Management:**
- Use TanStack Query for session creation (`useQuery` with `staleTime: Infinity`)
- Use `useMutation` for submit attempts
- Local state: `currentIndex`, `showFeedback`, `lastEvaluation`

**UX Flow:**
1. Create session on mount → fetch exercises
2. Show ExerciseCard + ResponseInput
3. On submit → show FeedbackDisplay with evaluation
4. User rates confidence → advance to next exercise
5. When complete → show SessionComplete summary

**Deliverables:**
- [ ] `PracticeSession.tsx` — Main session orchestrator
- [ ] `ExerciseCard.tsx` — Exercise display with type-specific rendering
- [ ] `SessionProgress.tsx` — Progress bar and stats
- [ ] `SessionComplete.tsx` — Session summary and next actions

**Estimated Time:** 10 hours

---

#### Task 7B.2: Response Input Components

**File:** `frontend/src/components/practice/ResponseInput.tsx`

| Exercise Type | Input Component | Features |
|---------------|-----------------|----------|
| Text exercises (free_recall, self_explain, teach_back) | `Textarea` | Placeholder per type, character count |
| Code exercises (debugging, code_completion, implementation) | Monaco `CodeEditor` | Syntax highlighting, line numbers, language detection |

**Behavior:**
- Cmd/Ctrl+Enter to submit
- Clear button for code editor
- Loading state during submission
- Exercise-type-specific placeholders

**Deliverables:**
- [ ] `ResponseInput.tsx` — Adaptive input based on exercise type
- [ ] Monaco editor integration
- [ ] Keyboard shortcuts

**Estimated Time:** 6 hours

---

#### Task 7B.3: Feedback Display Components

**File:** `frontend/src/components/practice/FeedbackDisplay.tsx`

| Section | Content |
|---------|---------|
| Result Header | Correct/incorrect icon, score percentage |
| Detailed Feedback | LLM feedback markdown, specific feedback points with icons |
| Model Answer | Revealed if incorrect (code diff for code exercises) |
| Confidence Rating | 4 buttons: "Still confused" → "Easy!" (1-4 scale) |

**Deliverables:**
- [ ] `FeedbackDisplay.tsx` — Evaluation results display
- [ ] `CodeDiff.tsx` — Side-by-side code comparison
- [ ] Confidence rating buttons

**Estimated Time:** 6 hours

---

### Phase 8B: Review Queue Frontend (Days 33-38)

The Review Queue UI handles spaced repetition card review—showing due cards and collecting user ratings.

#### Task 8B.1: Review Queue Components

**Directory:** `frontend/src/components/review/`

| Component | Props | Purpose |
|-----------|-------|---------|
| `ReviewQueue` | - | Main container - fetches due cards, manages review flow |
| `FlashCard` | `card`, `showAnswer`, `onShowAnswer` | Flip card with front/back, tap to reveal |
| `RatingButtons` | `onRate`, `isLoading`, `card` | FSRS rating buttons (Again/Hard/Good/Easy) with interval preview |
| `ReviewStats` | `remaining`, `reviewed`, `dueToday` | Session statistics |
| `ReviewComplete` | `reviewedCount`, `nextDueDate` | Completion screen |

**State Management:**
- `useQuery(['due-cards'])` - fetch due cards (staleTime: 5 min)
- `useMutation` for rating - invalidates due-cards query on success
- Local state: `showAnswer`, `reviewedCount`, `showAnswerTime` (for response timing)

**FlashCard Component:**
- Shows card front (question) with type badge, streak indicator, interval
- "Show Answer" button reveals back with animation
- Supports code blocks for both front and back
- Optional explanation section

**RatingButtons Component:**
- 4 buttons: Again (red), Hard (orange), Good (green), Easy (blue)
- Shows predicted next interval for each rating
- Keyboard shortcuts: 1-4

**Deliverables:**
- [ ] `ReviewQueue.tsx` — Due card queue management
- [ ] `FlashCard.tsx` — Card display with flip animation
- [ ] `RatingButtons.tsx` — FSRS rating interface
- [ ] `ReviewStats.tsx` — Session statistics
- [ ] `ReviewComplete.tsx` — Completion screen with next due info

**Estimated Time:** 10 hours

---

### Phase 8C: Analytics Dashboard Frontend (Days 39-45)

The Analytics Dashboard provides visual insight into learning progress, mastery levels, and areas needing attention.

#### Task 8C.1: Analytics Overview Components

**Directory:** `frontend/src/components/analytics/`

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| `AnalyticsDashboard` | Main container | Fetches overview data, responsive grid layout |
| `StatsCards` | Key metrics | Total cards, cards reviewed today, streak, avg retention |
| `MasteryOverview` | Topic mastery | Progress bars per topic, trend indicators, overall % |
| `WeakSpotsPanel` | Areas needing attention | Topics below threshold, "Practice now" buttons |
| `LearningCurve` | Progress over time | Recharts line chart (mastery, retention, cards reviewed) |
| `PracticeHeatmap` | Activity visualization | GitHub-style heatmap of practice days |
| `TopicMasteryTree` | Hierarchical view | Tree visualization of topic→subtopic mastery |

**Layout:**
```
┌─────────────────────────────────────────────┐
│  Learning Analytics                          │
├─────────────────────────────────────────────┤
│  [StatsCards - 4 columns]                   │
├──────────────────────┬──────────────────────┤
│  MasteryOverview     │  WeakSpotsPanel      │
├──────────────────────┴──────────────────────┤
│  LearningCurve (full width)                 │
├──────────────────────┬──────────────────────┤
│  PracticeHeatmap     │  TopicMasteryTree    │
└──────────────────────┴──────────────────────┘
```

**MasteryOverview Features:**
- Sort topics by mastery score
- Progress bar with color coding (green ≥80%, yellow ≥60%, orange ≥40%, red <40%)
- Trend indicators (↑ improving, ↓ declining, — stable)
- "View all N topics" link

**WeakSpotsPanel Features:**
- Query topics where mastery < 0.6
- Show recommendation per topic
- "Practice Now" button → navigates to /practice/{topicId}

**LearningCurve Component:**
- Uses Recharts `LineChart` with two lines: mastery (primary), retention (secondary)
- Query last 30 days of data
- X-axis: dates, Y-axis: 0-100%

**Deliverables:**
- [ ] `AnalyticsDashboard.tsx` — Main dashboard layout
- [ ] `MasteryOverview.tsx` — Topic mastery progress bars
- [ ] `WeakSpotsPanel.tsx` — Areas needing attention
- [ ] `LearningCurve.tsx` — Progress over time chart (Recharts)
- [ ] `PracticeHeatmap.tsx` — Activity calendar heatmap
- [ ] `TopicMasteryTree.tsx` — Hierarchical topic visualization
- [ ] `StatsCards.tsx` — Key metrics (streak, cards reviewed, etc.)

**Estimated Time:** 12 hours

---

#### Task 8C.2: API Client Layer

**Directory:** `frontend/src/api/`

| File | Methods |
|------|---------|
| `practice.ts` | `createSession`, `submitAttempt`, `updateConfidence`, `generateExercise`, `getSessionSummary` |
| `review.ts` | `getDueCards`, `rateCard`, `getCard`, `getCardsByTopic` |
| `analytics.ts` | `getOverview`, `getMastery`, `getWeakSpots`, `getLearningCurve`, `getPracticeHistory` |

**TypeScript Types (`frontend/src/types/learning.ts`):**

| Type | Fields |
|------|--------|
| `ExerciseType` | Union: free_recall, self_explain, worked_example, debugging, code_completion, implementation, teach_back, etc. |
| `CardType` | Union: concept, fact, application, cloze, code |
| `Rating` | Union: again, hard, good, easy |
| `Trend` | Union: improving, stable, declining |
| `Exercise` | id, exercise_type, prompt, context?, code_snippet?, language?, difficulty, topic_path?, hints? |
| `AttemptEvaluation` | is_correct, score, feedback, model_answer?, specific_feedback[] |
| `SpacedRepCard` | id, front, back, card_type, code_front?, code_back?, due_date, stability, difficulty, interval_days, streak |
| `MasteryState` | topic_path, mastery_score, success_rate, practice_count, trend |
| `SessionResponse` | id, exercises[], correct_count, total_count |
| `DueCardsResponse` | cards[], totalDueToday, nextDue? |
| `AnalyticsOverview` | stats, mastery[] |

**Deliverables:**
- [ ] `frontend/src/api/practice.ts` — Practice API client
- [ ] `frontend/src/api/review.ts` — Review API client
- [ ] `frontend/src/api/analytics.ts` — Analytics API client
- [ ] `frontend/src/types/learning.ts` — TypeScript type definitions

**Estimated Time:** 6 hours

---

#### Task 8C.3: Frontend Routes & Navigation

**Routes to add:**

| Path | Component | Description |
|------|-----------|-------------|
| `/practice` | PracticeSession | Start practice session (no topic filter) |
| `/practice/:topicId` | PracticeSession | Practice specific topic |
| `/review` | ReviewQueue | Spaced repetition review |
| `/analytics` | AnalyticsDashboard | Learning analytics overview |
| `/analytics/:topicId` | AnalyticsDashboard | Topic-specific analytics |

**Implementation Notes:**
- Use React lazy loading for code splitting
- Add to main navigation menu
- Integrate breadcrumbs for topic paths

**Deliverables:**
- [ ] Learning system routes
- [ ] Navigation menu updates
- [ ] Page components with lazy loading

**Estimated Time:** 3 hours

---

### Frontend Implementation Summary

| Task | Component | Estimated Hours |
|------|-----------|-----------------|
| 7B.1 | Practice Session Core | 10 |
| 7B.2 | Response Input Components | 6 |
| 7B.3 | Feedback Display | 6 |
| 8B.1 | Review Queue Components | 10 |
| 8C.1 | Analytics Dashboard | 12 |
| 8C.2 | API Client Layer | 6 |
| 8C.3 | Routes & Navigation | 3 |
| **Total** | | **53 hours** |

### Frontend Dependencies

| Package | Purpose |
|---------|---------|
| `@monaco-editor/react` | Code editor for code exercises |
| `recharts` | Charts for analytics dashboard |
| `framer-motion` | Animations for cards and transitions |
| `@tanstack/react-query` | Data fetching and caching |

---

## 4. API Endpoints

### 4.1 Practice API Router

**File:** `backend/app/routers/practice.py`

| Method | Endpoint | Request | Response | Description |
|--------|----------|---------|----------|-------------|
| POST | `/api/practice/session` | SessionCreateRequest | SessionResponse | Create balanced practice session |
| POST | `/api/practice/session/{id}/end` | - | SessionSummary | End session, get summary |
| POST | `/api/practice/exercise/generate` | ExerciseGenerateRequest | ExerciseResponse | Generate exercise for topic |
| POST | `/api/practice/submit` | AttemptSubmitRequest | AttemptEvaluationResponse | Submit response, get LLM feedback |
| PATCH | `/api/practice/attempt/{id}/confidence` | AttemptConfidenceUpdate | status | Update post-feedback confidence |

**Dependency:** `get_session_service()` - injects SessionService with SpacedRepService, ExerciseGenerator, MasteryService

### 4.2 Review API Router

**File:** `backend/app/routers/review.py`

| Method | Endpoint | Request | Response | Description |
|--------|----------|---------|----------|-------------|
| GET | `/api/review/due` | limit, topic (query) | DueCardsResponse | Get cards due for review |
| POST | `/api/review/rate` | CardReviewRequest | CardReviewResponse | Submit FSRS rating |
| POST | `/api/review/cards` | CardCreate | CardResponse | Create new card |
| GET | `/api/review/stats` | - | dict | Card statistics by state |

### 4.3 Analytics API Router

**File:** `backend/app/routers/analytics.py`

| Method | Endpoint | Request | Response | Description |
|--------|----------|---------|----------|-------------|
| GET | `/api/analytics/mastery` | - | MasteryOverview | Overall mastery stats |
| GET | `/api/analytics/mastery/{topic}` | topic path param | MasteryState | Topic-specific mastery |
| GET | `/api/analytics/weak-spots` | limit (query) | WeakSpotsResponse | Topics needing attention |

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File:** `backend/tests/unit/test_fsrs.py`

| Test | Scenario | Expected Behavior |
|------|----------|-------------------|
| `test_new_card_again_rating` | AGAIN on new card | Goes to LEARNING, interval=1 |
| `test_new_card_good_rating` | GOOD on new card | Stays in LEARNING, stability > 0 |
| `test_new_card_easy_rating` | EASY on new card | Graduates to REVIEW immediately |
| `test_stability_increases_on_success` | GOOD on review card | stability increases |
| `test_lapse_decreases_stability` | AGAIN on review card | Goes to RELEARNING, lapses += 1 |
| `test_interval_calculation` | stability=10 | interval ≈ 10 days (for 90% retention) |

### 5.2 Integration Tests

**File:** `backend/tests/integration/test_practice_api.py`

| Test Class | Test | Scenario |
|------------|------|----------|
| TestPracticeAPI | `test_create_session` | POST /api/practice/session → 200, returns session_id, items |
| TestPracticeAPI | `test_generate_exercise` | POST /api/practice/exercise/generate → 200, returns prompt |
| TestReviewAPI | `test_get_due_cards` | GET /api/review/due → 200, returns cards, total_due |
| TestReviewAPI | `test_rate_card` | POST /api/review/rate → 200, was_correct=true, next_due_date |

---

## 6. Timeline Summary

### Backend Implementation (Days 1-35)

| Phase | Days | Tasks | Deliverables | Hours |
|-------|------|-------|--------------|-------|
| 6A | 1-3 | Database Schema | Migration, models, Pydantic schemas | 8 |
| 6B | 4-7 | FSRS Algorithm | Scheduler, service layer | 10 |
| 6C | 8-14 | Exercise Generation | Generator, evaluator, prompts | 14 |
| 6D | 15-19 | Code Sandbox | Docker sandbox, test runner | 10 |
| 7A | 20-25 | Practice Sessions API | Session service, endpoints | 12 |
| 8A | 26-35 | Mastery Tracking | Mastery service, snapshots, analytics API | 16 |
| **Subtotal** | | | | **70** |

### Frontend Implementation (Days 26-45)

| Phase | Days | Tasks | Deliverables | Hours |
|-------|------|-------|--------------|-------|
| 7B | 26-32 | Practice Session UI | Exercise cards, response inputs, feedback | 22 |
| 8B | 33-38 | Review Queue UI | Flashcards, ratings, queue management | 10 |
| 8C | 39-45 | Analytics Dashboard | Charts, mastery viz, weak spots | 21 |
| **Subtotal** | | | | **53** |

### Testing & Polish (Days 46-55)

| Phase | Days | Tasks | Deliverables | Hours |
|-------|------|-------|--------------|-------|
| 9A | 46-50 | Backend Testing | Unit tests, integration tests | 12 |
| 9B | 51-55 | Frontend Testing | Component tests, E2E tests | 10 |
| **Subtotal** | | | | **22** |

**Total Estimated Time:** ~145 hours (55 days at 2.5 hours/day)

### Gantt View

```text
Days:     1----5----10---15---20---25---30---35---40---45---50---55
Backend:  [=6A=][==6B==][====6C====][=6D=][==7A==][====8A====]
Frontend:                               [====7B====][=8B=][===8C===]
Testing:                                                      [=9A=][9B]
```

---

## 7. Success Criteria

### Functional Requirements
- [ ] FSRS algorithm correctly schedules reviews for 90% retention
- [ ] Exercises adapt to mastery level (novice gets worked examples)
- [ ] Code exercises execute safely in Docker sandbox
- [ ] Practice sessions balance cards, exercises, and weak spots
- [ ] Mastery tracking accurately reflects knowledge state
- [ ] Weak spot detection identifies struggling topics

### Performance Requirements
- [ ] Card review processing < 200ms
- [ ] Exercise generation < 5 seconds
- [ ] Code execution sandbox timeout enforced at 10s
- [ ] Session creation < 3 seconds
- [ ] Mastery calculation < 500ms per topic

### Quality Requirements
- [ ] Unit test coverage > 80% for FSRS module
- [ ] Integration tests for all API endpoints
- [ ] No critical security vulnerabilities in sandbox
- [ ] All database migrations reversible

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM generates poor exercises | High | Medium | Human review queue, quality filters |
| Docker sandbox escape | Critical | Low | Strict limits, non-root, network disabled |
| FSRS parameters not optimal | Medium | Medium | Allow parameter tuning per user |
| Exercise evaluation inconsistent | Medium | High | Rubric-based prompts, confidence scores |
| Mastery calculation too simple | Medium | Medium | Extensible design, multiple signals |
| Code execution timeout attacks | Medium | Medium | Hard timeout, container kill |

---

## 9. Extensibility Guide

### Adding New Exercise Types

1. Add enum value to `ExerciseTypeEnum`
2. Create prompt template in `EXERCISE_PROMPTS`
3. Add selection logic in `_select_exercise_type`
4. Update evaluation prompts if needed

### Adding New Languages to Sandbox

1. Add entry to `CodeSandbox.IMAGES`
2. Create test wrapper in `_create_test_wrapper`
3. Add Docker image to build pipeline

### Customizing FSRS Parameters

```python
# Per-user parameter optimization
custom_params = FSRSParameters(
    w=[...],  # Custom weights from review history
    request_retention=0.85,  # Lower for busy users
)
scheduler = FSRSScheduler(params=custom_params)
```

---

## 10. Related Documents

| Document | Purpose |
|----------|---------|
| `design_docs/05_learning_system.md` | Detailed design specification |
| `LEARNING_THEORY.md` | Research foundations |
| `00_foundation_implementation.md` | Database setup reference |
| `02_llm_processing_implementation.md` | LLM client integration |


