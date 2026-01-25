# Learning System Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `02_llm_processing_layer.md`, `07_frontend_application.md`

---

## 1. Overview

The Learning System implements research-backed techniques for knowledge retention and skill acquisition. It transforms passive content consumption into active learning through spaced repetition, retrieval practice, and adaptive exercises.

### Design Goals

1. **Research-Backed**: Every feature grounded in learning science
2. **Desirable Difficulties**: Prioritize generation over recognition
3. **Adaptive**: Adjust difficulty based on demonstrated mastery
4. **Low Friction**: Seamless integration into daily workflow
5. **Measurable Progress**: Track retention and identify weak spots

---

## 2. Learning Science Foundation

### 2.1 Key Research

| Research | Key Finding | System Implementation |
|----------|-------------|----------------------|
| **Ericsson et al. (1993)** | Deliberate practice requires targeted effort at skill edges with immediate feedback | Adaptive difficulty + instant LLM feedback on responses |
| **Bjork & Bjork (2011)** | Desirable difficulties enhance long-term retention | Spacing, interleaving, generation in all exercises |
| **Dunlosky et al. (2013)** | Practice testing and distributed practice highest utility | Spaced repetition + retrieval-based exercises |
| **Chi et al. (1994)** | Self-explanation builds correct mental models | Explicit prompts for explanation |
| **Van Gog et al. (2011)** | Worked examples before problems for novices | Adaptive difficulty based on mastery |

### 2.2 Deliberate Practice Principles

Ericsson's deliberate practice framework identifies key conditions for expert-level skill development:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DELIBERATE PRACTICE REQUIREMENTS                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. WELL-DEFINED GOALS                                                       │
│     └─► System breaks topics into specific, measurable learning objectives   │
│                                                                              │
│  2. PRACTICE AT THE EDGE OF ABILITY                                          │
│     └─► Adaptive difficulty keeps challenges in the "stretch zone"           │
│         • Too easy = no growth (mastery > 0.8 → increase difficulty)         │
│         • Too hard = frustration (mastery < 0.3 → provide scaffolding)       │
│                                                                              │
│  3. IMMEDIATE, INFORMATIVE FEEDBACK                                          │
│     └─► LLM evaluates responses instantly with specific corrections          │
│         • What was correct and why                                           │
│         • What was missing or wrong                                          │
│         • How to improve next time                                           │
│                                                                              │
│  4. HIGH REPETITION WITH FOCUS ON ERRORS                                     │
│     └─► Weak spot detection resurfaces struggling concepts                   │
│         • Failed cards reviewed more frequently (FSRS lapses)                │
│         • Misconceptions tracked and addressed                               │
│                                                                              │
│  5. MENTAL REPRESENTATION BUILDING                                           │
│     └─► Self-explanation and teach-back exercises build mental models        │
│         • Connect new knowledge to existing understanding                    │
│         • Explain relationships, not just facts                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Unlike naive practice (repetition without feedback), deliberate practice requires focused attention on weaknesses. The system automatically identifies and prioritizes weak spots rather than letting learners practice what they already know.

### 2.3 Design Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LEARNING EFFECTIVENESS SPECTRUM                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LOW UTILITY                                              HIGH UTILITY       │
│  (avoid)                                                  (prioritize)       │
│  ◄──────────────────────────────────────────────────────────────────────►   │
│                                                                              │
│  • Rereading            • Summarization        • Retrieval Practice         │
│  • Highlighting         • Keyword mnemonics    • Spaced Repetition          │
│  • Recognition quizzes  • Imagery              • Interleaved Practice       │
│                                                • Self-Explanation            │
│                                                • Generation (no notes)       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Spaced Repetition System

### 3.1 FSRS Algorithm

We implement **Free Spaced Repetition Scheduler (FSRS)**, an open-source algorithm that outperforms SM-2.

```python
# backend/app/services/spaced_rep.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
import math

class Rating(IntEnum):
    AGAIN = 1   # Complete failure to recall
    HARD = 2    # Recalled with significant difficulty
    GOOD = 3    # Recalled with some effort
    EASY = 4    # Recalled effortlessly

@dataclass
class FSRSParameters:
    """FSRS-4.5 default parameters."""
    w: list[float] = None  # 17 weight parameters
    
    def __post_init__(self):
        if self.w is None:
            # Default FSRS-4.5 parameters
            self.w = [
                0.4, 0.6, 2.4, 5.8,      # Initial stability
                4.93, 0.94, 0.86, 0.01,   # Difficulty
                1.49, 0.14, 0.94,         # Stability after success
                2.18, 0.05, 0.34, 1.26,   # Stability after failure
                0.29, 2.61                 # Additional factors
            ]

@dataclass
class CardState:
    """State of a spaced repetition card."""
    difficulty: float = 0.3      # 0-1, higher = harder
    stability: float = 1.0       # Days until 90% retention probability
    due_date: datetime = None
    last_review: datetime = None
    review_count: int = 0
    lapses: int = 0              # Times forgotten after learning

class FSRSScheduler:
    """FSRS scheduling algorithm."""
    
    def __init__(self, params: FSRSParameters = None):
        self.params = params or FSRSParameters()
        self.desired_retention = 0.9  # Target 90% recall
    
    def schedule_review(
        self, 
        card: CardState, 
        rating: Rating,
        review_time: datetime = None
    ) -> CardState:
        """Update card state after review."""
        
        review_time = review_time or datetime.now()
        
        # Calculate new difficulty
        new_difficulty = self._update_difficulty(card.difficulty, rating)
        
        # Calculate new stability
        if rating == Rating.AGAIN:
            # Lapse: stability drops significantly
            new_stability = self._stability_after_failure(
                card.stability, card.difficulty
            )
            new_lapses = card.lapses + 1
        else:
            # Success: stability increases
            new_stability = self._stability_after_success(
                card.stability, card.difficulty, rating
            )
            new_lapses = card.lapses
        
        # Calculate next review date
        interval = self._stability_to_interval(new_stability)
        new_due_date = review_time + timedelta(days=interval)
        
        return CardState(
            difficulty=new_difficulty,
            stability=new_stability,
            due_date=new_due_date,
            last_review=review_time,
            review_count=card.review_count + 1,
            lapses=new_lapses
        )
    
    def _update_difficulty(self, current: float, rating: Rating) -> float:
        """Update difficulty based on rating."""
        w = self.params.w
        delta = (rating - 3) / 3  # -0.67 to +0.33
        new_diff = current + w[6] * delta
        return max(0.1, min(1.0, new_diff))  # Clamp to [0.1, 1.0]
    
    def _stability_after_success(
        self, 
        stability: float, 
        difficulty: float, 
        rating: Rating
    ) -> float:
        """Calculate new stability after successful recall."""
        w = self.params.w
        
        # Base multiplier from rating
        rating_factor = {
            Rating.HARD: w[15],
            Rating.GOOD: 1.0,
            Rating.EASY: w[16]
        }[rating]
        
        # Stability increase formula
        new_stability = stability * (
            1 + math.exp(w[8]) *
            (11 - difficulty * 10) *
            math.pow(stability, -w[9]) *
            (math.exp((1 - self._retention(stability)) * w[10]) - 1) *
            rating_factor
        )
        
        return new_stability
    
    def _stability_after_failure(
        self, 
        stability: float, 
        difficulty: float
    ) -> float:
        """Calculate new stability after forgetting."""
        w = self.params.w
        
        new_stability = (
            w[11] *
            math.pow(difficulty, -w[12]) *
            (math.pow(stability + 1, w[13]) - 1) *
            math.exp((1 - self._retention(stability)) * w[14])
        )
        
        return max(0.1, new_stability)
    
    def _retention(self, stability: float) -> float:
        """Calculate retention probability at stability."""
        return math.pow(0.9, 1.0 / stability)
    
    def _stability_to_interval(self, stability: float) -> float:
        """Convert stability to review interval in days."""
        # Interval where retention probability equals desired retention
        return stability * math.log(self.desired_retention) / math.log(0.9)
```

### 3.2 Card Types

```python
from pydantic import BaseModel

class SpacedRepCard(BaseModel):
    """A spaced repetition card."""
    
    id: str
    card_type: str  # concept, fact, application, cloze
    
    # Content
    front: str              # Question/prompt
    back: str               # Answer
    context_note_id: str    # Link to source note
    
    # FSRS state
    difficulty: float = 0.3
    stability: float = 1.0
    due_date: datetime = None
    last_review: datetime = None
    review_count: int = 0
    lapses: int = 0
    
    # Metadata
    tags: list[str] = []
    created_at: datetime
    
class CardType:
    CONCEPT = "concept"      # "What is X?"
    FACT = "fact"            # Specific information
    APPLICATION = "application"  # "How would you use X for Y?"
    CLOZE = "cloze"          # Fill-in-the-blank
    
    # Code cards
    CODE_SYNTAX = "code_syntax"      # "Write the syntax for X"
    CODE_OUTPUT = "code_output"      # "What does this code output?"
    CODE_PATTERN = "code_pattern"    # "Implement the X pattern"
    API_USAGE = "api_usage"          # "How do you use X API?"
```

### 3.3 Card Generation

```python
async def generate_cards_from_content(
    content: UnifiedContent,
    concepts: ExtractionResult,
    mastery_questions: list[dict],
    llm_client: LLMClient
) -> list[SpacedRepCard]:
    """Generate spaced repetition cards from processed content."""
    
    cards = []
    
    # Generate concept cards
    for concept in concepts.concepts:
        if concept.importance == "core":
            cards.append(SpacedRepCard(
                id=str(uuid.uuid4()),
                card_type=CardType.CONCEPT,
                front=f"What is {concept.name}?",
                back=concept.definition,
                context_note_id=content.id,
                tags=[f"concept:{concept.name}"],
                created_at=datetime.now()
            ))
    
    # Convert mastery questions to cards
    for question in mastery_questions:
        cards.append(SpacedRepCard(
            id=str(uuid.uuid4()),
            card_type=CardType.APPLICATION,
            front=question["question"],
            back="\n".join(question.get("key_points", ["[Answer requires recall]"])),
            context_note_id=content.id,
            tags=[f"difficulty:{question.get('difficulty', 'intermediate')}"],
            created_at=datetime.now()
        ))
    
    return cards
```

---

## 4. Exercise Generation

### 4.1 Exercise Types

```python
from enum import Enum

class ExerciseType(str, Enum):
    FREE_RECALL = "free_recall"       # Explain without notes
    SELF_EXPLAIN = "self_explain"     # Explain connections
    WORKED_EXAMPLE = "worked_example" # Study then apply
    APPLICATION = "application"        # Apply to new context
    COMPARE_CONTRAST = "compare_contrast"
    TEACH_BACK = "teach_back"         # Explain to someone else
    DEBUG = "debug"                    # Find errors in code/logic
    
    # Coding exercises
    CODE_IMPLEMENT = "code_implement"     # Write code from scratch
    CODE_COMPLETE = "code_complete"       # Fill in missing code
    CODE_DEBUG = "code_debug"             # Fix buggy code
    CODE_REFACTOR = "code_refactor"       # Improve existing code
    CODE_EXPLAIN = "code_explain"         # Explain what code does

class Exercise(BaseModel):
    id: str
    exercise_type: ExerciseType
    topic: str
    difficulty: str  # foundational, intermediate, advanced
    
    prompt: str
    hints: list[str] = []
    expected_key_points: list[str] = []
    
    # For worked examples
    worked_example: str = None
    follow_up_problem: str = None
    
    # For coding exercises
    language: str = None              # python, pytorch, rust, etc.
    starter_code: str = None          # Initial code template
    solution_code: str = None         # Reference solution
    test_cases: list[dict] = []       # [{"input": ..., "expected": ...}]
    buggy_code: str = None            # For debug exercises
    
    # Tracking
    source_content_ids: list[str] = []
    estimated_time_minutes: int = 15
```

### 4.2 Adaptive Exercise Generation

```python
# backend/app/services/exercise_generator.py

EXERCISE_PROMPTS = {
    ExerciseType.FREE_RECALL: """
Generate a free-recall exercise for the topic: {topic}

Mastery Level: {mastery_level}
Previous Exercise Results: {previous_results}

The learner should explain {concept} from memory, without looking at notes.

Create:
1. A clear prompt asking them to explain/describe
2. 2-3 hints they can optionally reveal
3. Key points that a good answer should include

Return JSON:
{{
  "prompt": "Explain...",
  "hints": ["hint1", "hint2"],
  "expected_key_points": ["point1", "point2", "point3"]
}}
""",

    ExerciseType.SELF_EXPLAIN: """
Generate a self-explanation exercise.

Topic: {topic}
Context: {context}

Prompt the learner to explain:
- Why something works a certain way
- How it connects to what they already know
- What would happen if conditions changed

Return JSON with prompt and expected reasoning elements.
""",

    ExerciseType.WORKED_EXAMPLE: """
Generate a worked example for a novice learner.

Topic: {topic}
Complexity: {complexity}

Create:
1. A worked example showing step-by-step solution
2. A follow-up problem for the learner to solve
3. Key principles demonstrated

The follow-up should be similar but not identical.

Return JSON:
{{
  "worked_example": "Step 1:...",
  "follow_up_problem": "Now try:...",
  "principles": ["principle1", "principle2"]
}}
""",

    # ─────────────────────────────────────────────────────────────
    # CODING EXERCISE PROMPTS
    # ─────────────────────────────────────────────────────────────
    
    ExerciseType.CODE_IMPLEMENT: """
Generate a coding implementation exercise.

Topic: {topic}
Language: {language}
Mastery Level: {mastery_level}
Libraries/Frameworks: {frameworks}

Create a focused coding task that requires implementing {concept}.

Return JSON:
{{
  "prompt": "Clear description of what to implement",
  "starter_code": "# Template with function signature and docstring\\ndef function_name(params):\\n    '''Docstring explaining requirements'''\\n    pass",
  "solution_code": "Complete working solution",
  "test_cases": [
    {{"input": "example_input", "expected": "expected_output"}},
    {{"input": "edge_case", "expected": "edge_output"}}
  ],
  "hints": ["hint1", "hint2"],
  "expected_key_points": ["Uses X correctly", "Handles edge case Y"]
}}
""",

    ExerciseType.CODE_COMPLETE: """
Generate a code completion exercise.

Topic: {topic}
Language: {language}
Mastery Level: {mastery_level}

Create code with strategic blanks (marked as ___) for the learner to fill in.
Focus on the most important parts that test understanding of {concept}.

Return JSON:
{{
  "prompt": "Complete the following code to [goal]",
  "starter_code": "Code with ___ blanks for key parts",
  "solution_code": "Complete working code",
  "blanks_explanation": ["blank1 should be X because...", "blank2 tests understanding of Y"],
  "test_cases": [{{"input": "...", "expected": "..."}}]
}}
""",

    ExerciseType.CODE_DEBUG: """
Generate a debugging exercise.

Topic: {topic}
Language: {language}
Bug Types to Include: {bug_types}

Create buggy code with realistic mistakes related to {concept}.
Include 1-3 bugs that test common misconceptions.

Return JSON:
{{
  "prompt": "Find and fix the bug(s) in this code",
  "buggy_code": "Code with intentional bugs",
  "solution_code": "Corrected code",
  "bugs": [
    {{"line": 5, "issue": "description", "fix": "how to fix"}},
  ],
  "hints": ["Look at line X", "Check the return type"],
  "test_cases": [{{"input": "...", "expected": "..."}}]
}}
""",

    ExerciseType.CODE_EXPLAIN: """
Generate a code explanation exercise.

Topic: {topic}
Language: {language}

Create code that demonstrates {concept} and ask the learner to explain:
1. What the code does
2. Why it works that way
3. What would happen if X changed

Return JSON:
{{
  "prompt": "Explain what this code does and why",
  "code_to_explain": "Interesting code demonstrating the concept",
  "expected_key_points": [
    "Should identify X",
    "Should explain why Y",
    "Should note the purpose of Z"
  ],
  "follow_up_questions": ["What if we changed A?", "Why not use B instead?"]
}}
"""
}

async def generate_exercise(
    topic: str,
    exercise_type: ExerciseType,
    mastery_level: float,
    previous_results: list[dict],
    llm_client: LLMClient
) -> Exercise:
    """Generate an exercise adapted to the learner's level."""
    
    # Determine difficulty based on mastery
    if mastery_level < 0.3:
        difficulty = "foundational"
        # Novices get worked examples first
        if exercise_type != ExerciseType.WORKED_EXAMPLE:
            exercise_type = ExerciseType.WORKED_EXAMPLE
    elif mastery_level < 0.7:
        difficulty = "intermediate"
    else:
        difficulty = "advanced"
    
    # Get relevant context
    context = await get_topic_context(topic)
    
    prompt_template = EXERCISE_PROMPTS.get(exercise_type)
    prompt = prompt_template.format(
        topic=topic,
        concept=topic,
        mastery_level=mastery_level,
        previous_results=json.dumps(previous_results[-5:]),  # Last 5 attempts
        context=context,
        complexity=difficulty
    )
    
    response = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response)
    
    return Exercise(
        id=str(uuid.uuid4()),
        exercise_type=exercise_type,
        topic=topic,
        difficulty=difficulty,
        prompt=result.get("prompt", result.get("follow_up_problem")),
        hints=result.get("hints", []),
        expected_key_points=result.get("expected_key_points", result.get("principles", [])),
        worked_example=result.get("worked_example"),
        follow_up_problem=result.get("follow_up_problem")
    )
```

### 4.3 Response Evaluation

```python
EVALUATION_PROMPT = """
Evaluate this learner's response to a practice exercise.

Exercise:
{prompt}

Expected Key Points:
{key_points}

Learner's Response:
{response}

Evaluate:
1. Which key points were covered (with examples from their response)?
2. Which key points were missing or incorrect?
3. What misconceptions are evident?
4. Overall quality score (1-5)

Return JSON:
{{
  "covered_points": [
    {{"point": "...", "evidence": "quote from response", "quality": "full|partial|incorrect"}}
  ],
  "missing_points": ["point1", "point2"],
  "misconceptions": ["misconception1"],
  "overall_score": 1-5,
  "specific_feedback": "Personalized feedback...",
  "suggested_review": ["concept to review"]
}}
"""

async def evaluate_response(
    exercise: Exercise,
    response: str,
    llm_client: LLMClient
) -> dict:
    """Evaluate learner's response and provide feedback."""
    
    prompt = EVALUATION_PROMPT.format(
        prompt=exercise.prompt,
        key_points="\n".join(f"- {p}" for p in exercise.expected_key_points),
        response=response
    )
    
    result = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(result)
```

### 4.4 Code Exercise Evaluation

```python
# backend/app/services/code_evaluator.py

import docker
import asyncio
import tempfile
import uuid
from pathlib import Path

class CodeEvaluator:
    """Evaluates coding exercise submissions in isolated Docker containers."""
    
    # Docker images for each language (pre-built with minimal dependencies)
    SANDBOX_IMAGES = {
        "python": {
            "image": "second-brain/sandbox-python:latest",
            "ext": ".py",
            "cmd": "python3 /code/submission.py"
        },
        "pytorch": {
            "image": "second-brain/sandbox-pytorch:latest",
            "ext": ".py",
            "cmd": "python3 /code/submission.py"
        },
        "javascript": {
            "image": "second-brain/sandbox-node:latest",
            "ext": ".js",
            "cmd": "node /code/submission.js"
        },
        "rust": {
            "image": "second-brain/sandbox-rust:latest",
            "ext": ".rs",
            "cmd": "cd /code && rustc submission.rs -o submission && ./submission"
        },
    }
    
    # Security constraints for containers
    CONTAINER_LIMITS = {
        "mem_limit": "128m",          # 128 MB memory limit
        "memswap_limit": "128m",      # No swap
        "cpu_period": 100000,
        "cpu_quota": 50000,           # 50% of one CPU
        "network_disabled": True,     # No network access
        "read_only": True,            # Read-only filesystem (except /tmp)
        "pids_limit": 50,             # Limit number of processes
    }
    
    def __init__(
        self, 
        llm_client, 
        timeout_seconds: int = 10,
        docker_client: docker.DockerClient = None
    ):
        self.llm_client = llm_client
        self.timeout = timeout_seconds
        self.docker = docker_client or docker.from_env()
    
    async def evaluate_code(
        self,
        exercise: Exercise,
        submitted_code: str
    ) -> dict:
        """Evaluate submitted code against test cases and quality criteria."""
        
        result = {
            "tests_passed": 0,
            "tests_total": len(exercise.test_cases),
            "test_results": [],
            "execution_error": None,
            "quality_feedback": None,
            "overall_score": 0.0
        }
        
        # Step 1: Run test cases in Docker container
        if exercise.test_cases:
            test_results = await self._run_tests(
                submitted_code, 
                exercise.test_cases,
                exercise.language
            )
            result["test_results"] = test_results
            result["tests_passed"] = sum(1 for t in test_results if t["passed"])
        
        # Step 2: LLM code review for quality
        quality_feedback = await self._review_code_quality(
            exercise=exercise,
            submitted_code=submitted_code
        )
        result["quality_feedback"] = quality_feedback
        
        # Step 3: Calculate overall score
        test_score = result["tests_passed"] / max(1, result["tests_total"])
        quality_score = quality_feedback.get("quality_score", 0.5) / 5.0
        result["overall_score"] = (test_score * 0.6) + (quality_score * 0.4)
        
        return result
    
    async def _run_tests(
        self, 
        code: str, 
        test_cases: list[dict],
        language: str
    ) -> list[dict]:
        """Execute code against test cases in isolated Docker container."""
        
        results = []
        sandbox_config = self.SANDBOX_IMAGES.get(
            language, 
            self.SANDBOX_IMAGES["python"]
        )
        
        for i, test in enumerate(test_cases):
            try:
                # Create test wrapper
                test_code = self._create_test_wrapper(code, test, language)
                
                # Run in Docker sandbox
                output = await self._execute_in_container(
                    test_code,
                    sandbox_config
                )
                
                passed = output.strip() == str(test["expected"]).strip()
                results.append({
                    "test_index": i,
                    "passed": passed,
                    "input": test["input"],
                    "expected": test["expected"],
                    "actual": output.strip(),
                    "error": None
                })
                
            except asyncio.TimeoutError:
                results.append({
                    "test_index": i,
                    "passed": False,
                    "input": test["input"],
                    "expected": test["expected"],
                    "actual": None,
                    "error": f"Execution timed out after {self.timeout}s"
                })
            except Exception as e:
                results.append({
                    "test_index": i,
                    "passed": False,
                    "input": test["input"],
                    "expected": test["expected"],
                    "actual": None,
                    "error": str(e)
                })
        
        return results
    
    async def _execute_in_container(
        self, 
        code: str, 
        sandbox_config: dict
    ) -> str:
        """Execute code in an isolated Docker container."""
        
        container = None
        temp_dir = None
        
        try:
            # Create temporary directory with code file
            temp_dir = tempfile.mkdtemp(prefix="sandbox_")
            code_file = Path(temp_dir) / f"submission{sandbox_config['ext']}"
            code_file.write_text(code)
            
            # Run container with strict security limits
            container = self.docker.containers.run(
                image=sandbox_config["image"],
                command=sandbox_config["cmd"],
                volumes={
                    temp_dir: {"bind": "/code", "mode": "ro"}  # Read-only mount
                },
                tmpfs={"/tmp": "size=10m,mode=1777"},  # Small writable /tmp
                detach=True,
                remove=False,  # We'll remove manually after getting logs
                **self.CONTAINER_LIMITS
            )
            
            # Wait for completion with timeout
            exit_code = await asyncio.wait_for(
                asyncio.to_thread(container.wait),
                timeout=self.timeout
            )
            
            # Get output
            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()
            
            if exit_code["StatusCode"] != 0:
                raise RuntimeError(f"Exit code {exit_code['StatusCode']}: {stderr}")
            
            return stdout
            
        finally:
            # Cleanup: always remove container and temp files
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            if temp_dir:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _create_test_wrapper(
        self, 
        code: str, 
        test: dict, 
        language: str
    ) -> str:
        """Wrap submitted code with test harness."""
        
        if language in ("python", "pytorch"):
            return f'''
{code}

# Test harness
if __name__ == "__main__":
    test_input = {repr(test["input"])}
    result = solution(test_input)
    print(result)
'''
        elif language == "javascript":
            return f'''
{code}

// Test harness
const testInput = {json.dumps(test["input"])};
const result = solution(testInput);
console.log(result);
'''
        else:
            return code
    
    async def _review_code_quality(
        self,
        exercise: Exercise,
        submitted_code: str
    ) -> dict:
        """Use LLM to review code quality and style."""
        
        # Build prompt with code blocks
        code_fence = "'''"  # Using triple quotes for inner code display
        prompt = f"""Review this code submission for a learning exercise.

Exercise: {exercise.prompt}
Language: {exercise.language}

Submitted Code:
{code_fence}
{submitted_code}
{code_fence}

Reference Solution:
{code_fence}
{exercise.solution_code}
{code_fence}

Evaluate:
1. Correctness of approach
2. Code style and readability
3. Efficiency considerations
4. Use of language idioms
5. Any bugs or issues

Return JSON:
{{
  "quality_score": 1-5,
  "correctness": "correct|partial|incorrect",
  "style_feedback": "Feedback on code style...",
  "efficiency_notes": "Any performance considerations...",
  "improvements": ["suggestion1", "suggestion2"],
  "bugs_found": ["bug1 if any"],
  "positive_aspects": ["good thing about the code"]
}}
"""
        
        result = await self.llm_client.complete(
            task="code_review",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(result)
```

#### Docker Sandbox Images

Pre-built Docker images for each supported language, designed for security:

```dockerfile
# docker/sandbox-python/Dockerfile
FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -s /bin/bash sandbox
USER sandbox

# No pip install allowed at runtime - pre-install common packages
# Image is intentionally minimal

WORKDIR /code
```

```dockerfile
# docker/sandbox-pytorch/Dockerfile
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# Security hardening
RUN useradd -m -s /bin/bash sandbox && \
    pip install --no-cache-dir numpy pandas matplotlib && \
    rm -rf /root/.cache

USER sandbox
WORKDIR /code
```

```yaml
# docker-compose.sandbox.yml
version: '3.8'

services:
  sandbox-builder:
    build:
      context: ./docker/sandbox-python
    image: second-brain/sandbox-python:latest
    
  sandbox-pytorch:
    build:
      context: ./docker/sandbox-pytorch
    image: second-brain/sandbox-pytorch:latest
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          devices:
            - driver: nvidia
              count: 0  # No GPU for exercises by default
              capabilities: [gpu]
```

**Security Features:**
- **No network access**: Containers cannot make external requests
- **Memory limits**: Prevents memory exhaustion attacks
- **CPU limits**: Prevents CPU exhaustion
- **Read-only filesystem**: Cannot modify system files
- **Non-root user**: Reduced privilege execution
- **Process limits**: Prevents fork bombs
- **Timeout enforcement**: Kills runaway processes

### 4.5 Example: PyTorch Exercise Generation

```python
# Example: Generate PyTorch-specific exercises

PYTORCH_EXERCISE_TEMPLATES = {
    "tensor_operations": {
        "topics": ["broadcasting", "indexing", "reshaping", "dtype conversion"],
        "example_prompt": "Implement a function that normalizes a batch of images",
    },
    "autograd": {
        "topics": ["gradient computation", "detach", "no_grad", "backward"],
        "example_prompt": "Manually compute gradients for a simple neural network",
    },
    "nn_module": {
        "topics": ["custom layers", "forward pass", "parameter registration"],
        "example_prompt": "Create a custom attention layer using nn.Module",
    },
    "data_loading": {
        "topics": ["Dataset", "DataLoader", "transforms", "collate_fn"],
        "example_prompt": "Implement a custom Dataset for image-text pairs",
    },
    "training_loop": {
        "topics": ["loss computation", "optimizer step", "gradient clipping"],
        "example_prompt": "Write a training loop with gradient accumulation",
    }
}

async def generate_pytorch_exercise(
    topic: str,
    mastery_level: float,
    llm_client: LLMClient
) -> Exercise:
    """Generate a PyTorch-specific coding exercise."""
    
    template = PYTORCH_EXERCISE_TEMPLATES.get(topic, {})
    
    prompt = f"""Generate a PyTorch coding exercise.

Topic: {topic}
Sub-topics to potentially cover: {template.get('topics', [])}
Mastery Level: {mastery_level}

Requirements:
- Use PyTorch best practices
- Include realistic tensor shapes (batch_size, channels, height, width)
- Test both correctness and proper use of PyTorch APIs
- For beginners (mastery < 0.3): Focus on single concept with hints
- For intermediate (0.3-0.7): Combine 2-3 concepts
- For advanced (> 0.7): Include optimization or edge cases

Return JSON with:
- prompt: Clear problem statement
- starter_code: Template with imports and function signature
- solution_code: Complete working solution
- test_cases: At least 2 test cases with tensor inputs/outputs
- hints: Progressive hints
- expected_key_points: What a good solution demonstrates
"""
    
    result = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    data = json.loads(result)
    
    return Exercise(
        id=str(uuid.uuid4()),
        exercise_type=ExerciseType.CODE_IMPLEMENT,
        topic=f"pytorch/{topic}",
        difficulty="foundational" if mastery_level < 0.3 else "intermediate" if mastery_level < 0.7 else "advanced",
        language="python",
        prompt=data["prompt"],
        starter_code=data["starter_code"],
        solution_code=data["solution_code"],
        test_cases=data["test_cases"],
        hints=data.get("hints", []),
        expected_key_points=data.get("expected_key_points", [])
    )
```

### 4.6 Code Card Generation

```python
async def generate_code_cards(
    content: UnifiedContent,
    language: str,
    llm_client: LLMClient
) -> list[SpacedRepCard]:
    """Generate spaced repetition cards for code concepts."""
    
    prompt = f"""Analyze this technical content and generate spaced repetition cards for coding practice.

Content:
{content.full_text[:4000]}

Language/Framework: {language}

Generate cards of these types:
1. CODE_SYNTAX: "Write the syntax for X" (front) → correct syntax (back)
2. CODE_OUTPUT: "What does this code output?" (front) → output + explanation (back)
3. API_USAGE: "How do you X in {language}?" (front) → code example (back)
4. CODE_PATTERN: "Implement the X pattern" (front) → implementation (back)

Return JSON array:
[
  {{
    "card_type": "code_syntax|code_output|api_usage|code_pattern",
    "front": "Question with code block if needed",
    "back": "Answer with code and explanation",
    "tags": ["tag1", "tag2"]
  }}
]

Focus on:
- Common APIs and patterns from the content
- Tricky syntax that's easy to forget
- Idiomatic usage patterns
"""
    
    result = await llm_client.complete(
        task="card_generation",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    cards_data = json.loads(result)
    
    return [
        SpacedRepCard(
            id=str(uuid.uuid4()),
            card_type=card["card_type"],
            front=card["front"],
            back=card["back"],
            context_note_id=content.id,
            tags=card.get("tags", []) + [f"lang:{language}"],
            created_at=datetime.now()
        )
        for card in cards_data
    ]
```

---

## 5. Mastery Tracking

### 5.1 Mastery Model

```python
@dataclass
class MasteryState:
    """Tracks mastery of a concept or topic."""
    
    concept_id: str
    topic_path: str
    
    # Core metrics
    mastery_score: float = 0.0      # 0-1, overall mastery
    confidence_avg: float = 0.0     # Average self-reported confidence
    
    # Practice history
    practice_count: int = 0
    success_rate: float = 0.0       # Correct / total attempts
    last_practiced: datetime = None
    
    # Spaced rep integration
    retention_estimate: float = 0.9  # Predicted recall probability
    days_since_review: int = 0
    
    # Trend
    trend: str = "stable"  # improving, stable, declining

def calculate_mastery(
    attempts: list[PracticeAttempt],
    card_states: list[CardState]
) -> float:
    """Calculate overall mastery score."""
    
    if not attempts:
        return 0.0
    
    # Weight recent attempts more heavily
    weights = [0.5 ** i for i in range(len(attempts))]
    weights = [w / sum(weights) for w in weights]
    
    # Calculate weighted success rate
    success_scores = [
        a.score * w 
        for a, w in zip(reversed(attempts), weights)
    ]
    recent_success = sum(success_scores)
    
    # Factor in spaced rep retention
    if card_states:
        avg_stability = sum(c.stability for c in card_states) / len(card_states)
        retention_factor = min(1.0, avg_stability / 30)  # Normalize to ~30 day stability
    else:
        retention_factor = 0.5
    
    # Combine factors
    mastery = (recent_success * 0.6) + (retention_factor * 0.4)
    
    return min(1.0, max(0.0, mastery))
```

### 5.2 Weak Spot Detection

```python
async def identify_weak_spots(
    user_id: str,
    min_attempts: int = 3,
    mastery_threshold: float = 0.6
) -> list[dict]:
    """Find topics where the learner is struggling."""
    
    # Get all mastery states
    mastery_states = await get_mastery_states(user_id)
    
    weak_spots = []
    
    for state in mastery_states:
        # Skip topics with insufficient practice
        if state.practice_count < min_attempts:
            continue
        
        # Check for low mastery
        if state.mastery_score < mastery_threshold:
            weak_spots.append({
                "topic": state.topic_path,
                "mastery_score": state.mastery_score,
                "success_rate": state.success_rate,
                "trend": state.trend,
                "days_since_practice": state.days_since_review,
                "recommendation": _generate_recommendation(state)
            })
    
    # Sort by urgency (low mastery + declining trend)
    weak_spots.sort(key=lambda x: (
        x["trend"] == "declining",
        -x["mastery_score"]
    ), reverse=True)
    
    return weak_spots

def _generate_recommendation(state: MasteryState) -> str:
    """Generate study recommendation for weak spot."""
    
    if state.trend == "declining":
        return "Urgent review needed - knowledge fading"
    elif state.success_rate < 0.5:
        return "Review foundational concepts before more practice"
    elif state.practice_count < 5:
        return "More practice needed to solidify understanding"
    else:
        return "Spaced review recommended"
```

---

## 6. Practice Session Flow

### 6.1 Session Generation

```python
async def generate_practice_session(
    user_id: str,
    duration_minutes: int = 15,
    topic_filter: str = None
) -> PracticeSession:
    """Generate a balanced practice session."""
    
    session_items = []
    
    # 1. Due spaced rep cards (40% of time)
    due_cards = await get_due_cards(user_id, limit=10)
    for card in due_cards[:int(duration_minutes * 0.4 / 2)]:
        session_items.append(SessionItem(
            type="spaced_rep",
            card=card,
            estimated_minutes=2
        ))
    
    # 2. Weak spot exercises (30% of time)
    weak_spots = await identify_weak_spots(user_id)
    if weak_spots:
        weak_topic = weak_spots[0]["topic"]
        mastery = await get_mastery_state(user_id, weak_topic)
        exercise = await generate_exercise(
            topic=weak_topic,
            exercise_type=ExerciseType.FREE_RECALL,
            mastery_level=mastery.mastery_score,
            previous_results=[],
            llm_client=get_llm_client()
        )
        session_items.append(SessionItem(
            type="exercise",
            exercise=exercise,
            estimated_minutes=int(duration_minutes * 0.3)
        ))
    
    # 3. New content (30% of time) - interleaved
    if topic_filter:
        new_topics = await get_unlearned_topics(user_id, topic_filter)
        for topic in new_topics[:2]:
            # Provide worked example for new topics
            exercise = await generate_exercise(
                topic=topic,
                exercise_type=ExerciseType.WORKED_EXAMPLE,
                mastery_level=0.0,
                previous_results=[],
                llm_client=get_llm_client()
            )
            session_items.append(SessionItem(
                type="exercise",
                exercise=exercise,
                estimated_minutes=int(duration_minutes * 0.15)
            ))
    
    # Shuffle for interleaving (but keep worked examples first for their topic)
    session_items = _interleave_items(session_items)
    
    return PracticeSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        items=session_items,
        estimated_duration=duration_minutes,
        created_at=datetime.now()
    )
```

---

## 7. Database Schema

```sql
-- Practice attempts
CREATE TABLE practice_attempts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID REFERENCES practice_sessions(id),
    
    -- What was practiced
    concept_id UUID,
    card_id UUID REFERENCES spaced_rep_cards(id),
    exercise_id UUID REFERENCES exercises(id),
    exercise_type VARCHAR(50),
    
    -- Response
    prompt TEXT NOT NULL,
    response TEXT,
    time_spent_seconds INT,
    
    -- Evaluation
    score FLOAT,  -- 0-1
    is_correct BOOLEAN,
    confidence_before FLOAT,
    confidence_after FLOAT,
    feedback TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Spaced repetition cards
CREATE TABLE spaced_rep_cards (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    
    -- Content
    card_type VARCHAR(50) NOT NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    context_note_id UUID,
    tags JSONB DEFAULT '[]',
    
    -- FSRS state
    difficulty FLOAT DEFAULT 0.3,
    stability FLOAT DEFAULT 1.0,
    due_date DATE,
    last_review TIMESTAMP,
    review_count INT DEFAULT 0,
    lapses INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cards_due ON spaced_rep_cards(user_id, due_date);
CREATE INDEX idx_cards_context ON spaced_rep_cards(context_note_id);

-- Mastery snapshots (daily aggregation)
CREATE TABLE mastery_snapshots (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    concept_id UUID,
    topic_path VARCHAR(255),
    
    mastery_score FLOAT,
    confidence_avg FLOAT,
    practice_count INT,
    success_rate FLOAT,
    
    snapshot_date DATE NOT NULL,
    
    UNIQUE(user_id, concept_id, snapshot_date)
);

CREATE INDEX idx_mastery_user_date ON mastery_snapshots(user_id, snapshot_date);
```

---

## 8. API Endpoints

```python
# backend/app/routers/practice.py

@router.post("/api/practice/session")
async def create_session(
    duration_minutes: int = 15,
    topic: str = None
) -> PracticeSession:
    """Generate a new practice session."""
    pass

@router.post("/api/practice/submit")
async def submit_response(
    item_id: str,
    response: str,
    time_spent_seconds: int,
    confidence: float
) -> EvaluationResult:
    """Submit response and get feedback."""
    pass

@router.get("/api/review/due")
async def get_due_cards(
    limit: int = 20
) -> list[SpacedRepCard]:
    """Get cards due for review."""
    pass

@router.post("/api/review/rate")
async def rate_card(
    card_id: str,
    rating: Rating
) -> CardState:
    """Update card after review."""
    pass

@router.get("/api/analytics/mastery")
async def get_mastery_overview() -> dict:
    """Get mastery scores by topic."""
    pass

@router.get("/api/analytics/weak-spots")
async def get_weak_spots() -> list[dict]:
    """Get topics needing attention."""
    pass
```

---

## 9. Configuration

```yaml
# config/learning.yaml
learning:
  spaced_rep:
    algorithm: "fsrs"
    desired_retention: 0.9
    max_interval_days: 365
    
  exercises:
    novice_threshold: 0.3
    intermediate_threshold: 0.7
    prefer_worked_examples_below: 0.3
    
  sessions:
    default_duration_minutes: 15
    spaced_rep_ratio: 0.4
    weak_spots_ratio: 0.3
    new_content_ratio: 0.3
    enable_interleaving: true
    
  mastery:
    min_attempts_for_score: 3
    recency_weight: 0.6
    weak_spot_threshold: 0.6
```

---

## 10. Related Documents

- `02_llm_processing_layer.md` — Question and card generation
- `07_frontend_application.md` — Practice session UI

