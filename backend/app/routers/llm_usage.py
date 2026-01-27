"""
LLM Usage API Router

Endpoints for LLM cost and usage tracking, providing visibility into
API spending and token consumption.

Endpoints:
- GET /api/llm-usage/daily - Get today's usage summary
- GET /api/llm-usage/monthly - Get current month's usage summary
- GET /api/llm-usage/budget - Get budget status and alerts
- GET /api/llm-usage/history - Get historical usage data
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.db.models import LLMUsageLog
from app.middleware.error_handling import handle_endpoint_errors
from app.services.cost_tracking import CostTracker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm-usage", tags=["llm-usage"])


# ===========================================
# Response Models
# ===========================================


class ModelBreakdown(BaseModel):
    """Usage breakdown by model."""
    model: str
    cost_usd: float
    request_count: int
    tokens: int = 0


class PipelineBreakdown(BaseModel):
    """Usage breakdown by pipeline."""
    pipeline: str
    cost_usd: float
    request_count: int


class DailyUsageResponse(BaseModel):
    """Daily usage summary response."""
    date: str
    total_cost_usd: float
    request_count: int
    total_tokens: int
    by_model: dict[str, dict]
    by_pipeline: dict[str, dict]


class MonthlyUsageResponse(BaseModel):
    """Monthly usage summary response."""
    year: int
    month: int
    total_cost_usd: float
    request_count: int
    total_tokens: int
    by_day: list[dict]
    by_model: dict[str, dict]


class BudgetStatusResponse(BaseModel):
    """Budget status and alerts response."""
    period: str = Field(description="Budget period (monthly/daily)")
    current_spend_usd: float = Field(description="Current spend in USD")
    limit_usd: float = Field(description="Budget limit in USD")
    remaining_usd: float = Field(description="Remaining budget in USD")
    percentage_used: float = Field(description="Percentage of budget used")
    is_over_budget: bool = Field(description="Whether budget is exceeded")
    alert_threshold: float = Field(description="Alert threshold percentage")
    is_alert_triggered: bool = Field(description="Whether alert threshold exceeded")


class UsageHistoryPoint(BaseModel):
    """Single point in usage history."""
    date: str
    cost_usd: float
    request_count: int
    tokens: int


class UsageHistoryResponse(BaseModel):
    """Historical usage data response."""
    period_days: int
    total_cost_usd: float
    total_requests: int
    total_tokens: int
    daily_data: list[UsageHistoryPoint]
    avg_daily_cost: float
    trend_direction: str = Field(description="up, down, or stable")


class TopConsumersResponse(BaseModel):
    """Top consumers of LLM resources."""
    by_model: list[ModelBreakdown]
    by_pipeline: list[PipelineBreakdown]
    by_operation: list[dict]


# ===========================================
# Endpoints
# ===========================================


@router.get("/daily", response_model=DailyUsageResponse)
@handle_endpoint_errors("Get daily usage")
async def get_daily_usage(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    db: AsyncSession = Depends(get_db),
) -> DailyUsageResponse:
    """
    Get LLM usage summary for a specific day.

    Returns:
    - Total cost and token count
    - Breakdown by model
    - Breakdown by pipeline
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.now(timezone.utc)

    summary = await CostTracker.get_daily_cost(date=target_date, session=db)
    return DailyUsageResponse(**summary)


@router.get("/monthly", response_model=MonthlyUsageResponse)
@handle_endpoint_errors("Get monthly usage")
async def get_monthly_usage(
    year: Optional[int] = Query(None, description="Year (defaults to current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month (defaults to current month)"),
    db: AsyncSession = Depends(get_db),
) -> MonthlyUsageResponse:
    """
    Get LLM usage summary for a specific month.

    Returns:
    - Total cost and token count
    - Daily breakdown
    - Breakdown by model
    """
    summary = await CostTracker.get_monthly_cost(year=year, month=month, session=db)
    return MonthlyUsageResponse(**summary)


@router.get("/budget", response_model=BudgetStatusResponse)
@handle_endpoint_errors("Get budget status")
async def get_budget_status(
    period: str = Query("monthly", description="Budget period: 'daily' or 'monthly'"),
    db: AsyncSession = Depends(get_db),
) -> BudgetStatusResponse:
    """
    Get current budget status and alerts.

    Checks spend against configured budget limits and returns
    whether alerts should be triggered.
    """
    limit_usd = settings.LITELLM_BUDGET_MAX
    alert_threshold = settings.LITELLM_BUDGET_ALERT

    result = await CostTracker.check_budget_limit(
        limit_usd=limit_usd,
        period=period,
        session=db,
    )

    return BudgetStatusResponse(
        period=result["period"],
        current_spend_usd=result["current_spend_usd"],
        limit_usd=result["limit_usd"],
        remaining_usd=result["remaining_usd"],
        percentage_used=result["percentage_used"],
        is_over_budget=result["is_over_budget"],
        alert_threshold=alert_threshold,
        is_alert_triggered=result["percentage_used"] >= alert_threshold,
    )


@router.get("/history", response_model=UsageHistoryResponse)
@handle_endpoint_errors("Get usage history")
async def get_usage_history(
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: AsyncSession = Depends(get_db),
) -> UsageHistoryResponse:
    """
    Get historical LLM usage data.

    Returns daily usage data for the specified period,
    along with aggregated totals and trend analysis.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Query daily aggregates
    daily_query = await db.execute(
        select(
            func.date(LLMUsageLog.created_at).label("date"),
            func.sum(LLMUsageLog.cost_usd).label("cost"),
            func.count(LLMUsageLog.id).label("count"),
            func.sum(LLMUsageLog.total_tokens).label("tokens"),
        )
        .where(LLMUsageLog.created_at >= start_date)
        .group_by(func.date(LLMUsageLog.created_at))
        .order_by("date")
    )

    daily_data = [
        UsageHistoryPoint(
            date=str(row.date),
            cost_usd=row.cost or 0,
            request_count=row.count or 0,
            tokens=row.tokens or 0,
        )
        for row in daily_query
    ]

    # Calculate totals
    total_cost = sum(d.cost_usd for d in daily_data)
    total_requests = sum(d.request_count for d in daily_data)
    total_tokens = sum(d.tokens for d in daily_data)
    avg_daily_cost = total_cost / days if days > 0 else 0

    # Calculate trend (compare last 7 days to previous 7 days)
    if len(daily_data) >= 14:
        recent = sum(d.cost_usd for d in daily_data[-7:])
        previous = sum(d.cost_usd for d in daily_data[-14:-7])
        if previous > 0:
            change_pct = ((recent - previous) / previous) * 100
            if change_pct > 10:
                trend = "up"
            elif change_pct < -10:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "up" if recent > 0 else "stable"
    else:
        trend = "stable"

    return UsageHistoryResponse(
        period_days=days,
        total_cost_usd=total_cost,
        total_requests=total_requests,
        total_tokens=total_tokens,
        daily_data=daily_data,
        avg_daily_cost=avg_daily_cost,
        trend_direction=trend,
    )


@router.get("/top-consumers", response_model=TopConsumersResponse)
@handle_endpoint_errors("Get top consumers")
async def get_top_consumers(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of top items to return"),
    db: AsyncSession = Depends(get_db),
) -> TopConsumersResponse:
    """
    Get top consumers of LLM resources.

    Identifies which models, pipelines, and operations are using
    the most tokens and generating the most cost.
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Top models by cost
    model_query = await db.execute(
        select(
            LLMUsageLog.model,
            func.sum(LLMUsageLog.cost_usd).label("cost"),
            func.count(LLMUsageLog.id).label("count"),
            func.sum(LLMUsageLog.total_tokens).label("tokens"),
        )
        .where(LLMUsageLog.created_at >= start_date)
        .group_by(LLMUsageLog.model)
        .order_by(func.sum(LLMUsageLog.cost_usd).desc())
        .limit(limit)
    )

    by_model = [
        ModelBreakdown(
            model=row.model or "unknown",
            cost_usd=row.cost or 0,
            request_count=row.count or 0,
            tokens=row.tokens or 0,
        )
        for row in model_query
    ]

    # Top pipelines by cost
    pipeline_query = await db.execute(
        select(
            LLMUsageLog.pipeline,
            func.sum(LLMUsageLog.cost_usd).label("cost"),
            func.count(LLMUsageLog.id).label("count"),
        )
        .where(
            LLMUsageLog.created_at >= start_date,
            LLMUsageLog.pipeline.isnot(None),
        )
        .group_by(LLMUsageLog.pipeline)
        .order_by(func.sum(LLMUsageLog.cost_usd).desc())
        .limit(limit)
    )

    by_pipeline = [
        PipelineBreakdown(
            pipeline=row.pipeline or "unknown",
            cost_usd=row.cost or 0,
            request_count=row.count or 0,
        )
        for row in pipeline_query
    ]

    # Top operations by cost
    operation_query = await db.execute(
        select(
            LLMUsageLog.operation,
            func.sum(LLMUsageLog.cost_usd).label("cost"),
            func.count(LLMUsageLog.id).label("count"),
            func.sum(LLMUsageLog.total_tokens).label("tokens"),
        )
        .where(
            LLMUsageLog.created_at >= start_date,
            LLMUsageLog.operation.isnot(None),
        )
        .group_by(LLMUsageLog.operation)
        .order_by(func.sum(LLMUsageLog.cost_usd).desc())
        .limit(limit)
    )

    by_operation = [
        {
            "operation": row.operation or "unknown",
            "cost_usd": row.cost or 0,
            "request_count": row.count or 0,
            "tokens": row.tokens or 0,
        }
        for row in operation_query
    ]

    return TopConsumersResponse(
        by_model=by_model,
        by_pipeline=by_pipeline,
        by_operation=by_operation,
    )
