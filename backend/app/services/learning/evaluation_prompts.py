"""
Evaluation Prompts

LLM prompts for evaluating learner responses to exercises.

These prompts are used by ResponseEvaluator to assess:
1. Text responses (explanations, definitions, conceptual answers)
2. Code responses (programming solutions)

Both prompts output structured JSON for programmatic parsing.
"""


# =============================================================================
# Text Response Evaluation
# =============================================================================

EVALUATION_PROMPT = """You are evaluating a learner's response to an exercise.

EXERCISE TYPE: {exercise_type}
TOPIC: {topic}
DIFFICULTY: {difficulty}

EXERCISE PROMPT:
{prompt}

EXPECTED KEY POINTS:
{key_points}

LEARNER'S RESPONSE:
{response}

Evaluate the response and return a JSON object with:
{{
    "covered_points": [
        {{"point": "key point text", "evidence": "quote from response showing coverage"}}
    ],
    "missing_points": [
        "key point that was not addressed"
    ],
    "misconceptions": [
        {{"error": "what was wrong", "correction": "what is correct", "explanation": "why"}}
    ],
    "overall_score": 4,  // 1-5 scale
    "specific_feedback": "Personalized feedback for the learner",
    "suggested_review": ["topics to review"]
}}

Scoring guide:
- 5: Excellent - covers all key points accurately with depth
- 4: Good - covers most key points with minor gaps
- 3: Adequate - covers core points but missing important details
- 2: Partial - significant gaps or misconceptions
- 1: Insufficient - major misconceptions or minimal coverage

Be encouraging but honest. Focus on specific improvements."""


# =============================================================================
# Code Response Evaluation
# =============================================================================

CODE_EVALUATION_PROMPT = """You are evaluating a learner's code solution.

EXERCISE TYPE: {exercise_type}
TOPIC: {topic}
DIFFICULTY: {difficulty}
LANGUAGE: {language}

EXERCISE PROMPT:
{prompt}

REFERENCE SOLUTION:
{solution_code}

LEARNER'S CODE:
{response_code}

TEST RESULTS:
{test_results}

Evaluate the code and return a JSON object with:
{{
    "covered_points": [
        {{"point": "concept demonstrated", "evidence": "relevant code snippet"}}
    ],
    "missing_points": [
        "concept or best practice not demonstrated"
    ],
    "misconceptions": [
        {{"error": "code issue", "correction": "how to fix it", "explanation": "why it matters"}}
    ],
    "overall_score": 4,  // 1-5 scale
    "specific_feedback": "Code review style feedback",
    "suggested_review": ["topics to study"]
}}

Scoring guide:
- 5: Excellent - all tests pass, clean idiomatic code, proper error handling, efficient solution
- 4: Good - all/most tests pass, readable code with minor style issues or small inefficiencies
- 3: Adequate - core functionality works, but has notable style issues, missing edge cases, or suboptimal approach
- 2: Partial - some tests fail, logic errors present, or significant code quality issues
- 1: Insufficient - most tests fail, fundamental misunderstanding of the problem or language

Consider:
- Correctness (test results)
- Code style and readability
- Efficiency where relevant
- Proper use of language features
- Edge case handling

Be encouraging but honest. Provide actionable feedback to help the learner improve."""
