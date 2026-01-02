"""
LLM API Utilities

Helper functions for working with LLM APIs, including model-specific
configuration adjustments.

Usage:
    from app.pipelines.utils.api_utils import adjust_temperature_for_model

    adjusted_temp = adjust_temperature_for_model("gemini/gemini-3-flash", 0.7)
"""


def adjust_temperature_for_model(model: str, temperature: float) -> float:
    """
    Adjust temperature based on model requirements.

    Some models have specific temperature requirements:
    - Gemini 3 models require temperature=1.0 to avoid infinite loops
      and degraded reasoning performance.

    Args:
        model: Model identifier (e.g., "gemini/gemini-3-flash-preview")
        temperature: Requested temperature value

    Returns:
        Adjusted temperature value appropriate for the model
    """
    # Gemini 3 models need temperature=1.0
    if "gemini-3" in model.lower() or "gemini/gemini-3" in model.lower():
        if temperature < 1.0:
            return 1.0

    return temperature

