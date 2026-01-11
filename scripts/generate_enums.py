#!/usr/bin/env python3
"""
Generate JavaScript/TypeScript enum constants from Python enum definitions.

This script reads Python enums from the backend and generates a corresponding
JavaScript constants file for the frontend. This ensures both codebases use
the same enum values and eliminates sync issues.

Usage:
    python scripts/generate_enums.py

The generated file will be written to:
    frontend/src/constants/enums.generated.js

Add this to your build process or run manually after modifying backend enums.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.enums.learning import (
    CardState,
    Rating,
    ExerciseType,
    ExerciseDifficulty,
    MasteryTrend,
    SessionType,
    CodeLanguage,
    TimePeriod,
    GroupBy,
)
from app.enums.content import ContentType, ProcessingStatus


def enum_to_js(enum_class, include_helpers: bool = False) -> str:
    """Convert a Python enum to JavaScript object literal."""
    name = enum_class.__name__

    # Get docstring for JSDoc
    docstring = enum_class.__doc__ or f"{name} enum values"
    docstring = docstring.strip().replace("\n", "\n * ")

    # Build object entries
    entries = []
    for member in enum_class:
        entries.append(f"  {member.name}: '{member.value}'")

    # Build the export
    lines = [
        f"/**",
        f" * {docstring}",
        f" */",
        f"export const {name} = Object.freeze({{",
        ",\n".join(entries),
        f"}})",
    ]

    return "\n".join(lines)


def generate_helper_sets() -> str:
    """Generate helper sets like CODE_EXERCISE_TYPES."""
    code_types = [et for et in ExerciseType if et.name.startswith("CODE_")]
    text_types = [et for et in ExerciseType if not et.name.startswith("CODE_")]

    return f"""
/**
 * Set of code-based exercise types.
 * Use: CODE_EXERCISE_TYPES.has(exerciseType)
 */
export const CODE_EXERCISE_TYPES = new Set([
  {",\n  ".join(f"ExerciseType.{et.name}" for et in code_types)}
])

/**
 * Set of text-based exercise types.
 * Use: TEXT_EXERCISE_TYPES.has(exerciseType)
 */
export const TEXT_EXERCISE_TYPES = new Set([
  {",\n  ".join(f"ExerciseType.{et.name}" for et in text_types)}
])

/**
 * Check if an exercise type is a code exercise.
 * @param {{string}} exerciseType - The exercise type value
 * @returns {{boolean}}
 */
export function isCodeExercise(exerciseType) {{
  return CODE_EXERCISE_TYPES.has(exerciseType)
}}

/**
 * Check if an exercise type is a text exercise.
 * @param {{string}} exerciseType - The exercise type value
 * @returns {{boolean}}
 */
export function isTextExercise(exerciseType) {{
  return TEXT_EXERCISE_TYPES.has(exerciseType)
}}
"""


def main():
    output_path = (
        Path(__file__).parent.parent
        / "frontend"
        / "src"
        / "constants"
        / "enums.generated.js"
    )

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Header
    header = f"""/**
 * AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * 
 * Generated from Python enums in backend/app/enums/
 * Run: python scripts/generate_enums.py
 * Generated at: {datetime.now().isoformat()}
 * 
 * This file ensures frontend and backend use the same enum values.
 */

"""

    # Generate enum objects
    enums_to_export = [
        ExerciseType,
        ExerciseDifficulty,
        CardState,
        Rating,
        MasteryTrend,
        SessionType,
        CodeLanguage,
        TimePeriod,
        GroupBy,
        ContentType,
        ProcessingStatus,
    ]

    sections = [header]

    for enum_class in enums_to_export:
        sections.append(enum_to_js(enum_class))
        sections.append("")  # blank line between enums

    # Add helper functions
    sections.append(generate_helper_sets())

    content = "\n".join(sections)

    # Write file
    output_path.write_text(content)
    print(f"✓ Generated {output_path}")
    print(f"  Exported {len(enums_to_export)} enums")


if __name__ == "__main__":
    main()
