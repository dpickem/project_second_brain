"""
LLM Cost Tracking Service

Provides centralized cost tracking for all LLM API calls.
Persists usage data to PostgreSQL for reporting and budget management.

Features:
- Async database persistence
- Batch logging for high-volume operations
- Daily/monthly cost aggregations
- Budget alerts and limits
- Cost reports by pipeline, model, or time period

Usage:
    from app.services.cost_tracking import CostTracker

    # Track a single usage
    await CostTracker.log_usage(usage)

    # Track multiple usages (batch)
    await CostTracker.log_usages_batch(usages)

    # Get cost summary
    summary = await CostTracker.get_daily_summary()
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session_maker
from app.db.models import LLMUsageLog, LLMCostSummary
from app.pipelines.utils.cost_types import LLMUsage

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Centralized LLM cost tracking service.

    Handles logging usage to the database and provides
    aggregation queries for cost reporting.
    """

    @staticmethod
    async def log_usage(
        usage: LLMUsage, session: Optional[AsyncSession] = None
    ) -> LLMUsageLog:
        """
        Log a single LLM usage record to the database.

        Args:
            usage: LLMUsage dataclass from completion call
            session: Optional existing database session

        Returns:
            Created LLMUsageLog database record
        """

        async def _log(session: AsyncSession) -> LLMUsageLog:
            log_entry = LLMUsageLog(
                request_id=usage.request_id,
                model=usage.model,
                provider=usage.provider,
                request_type=usage.request_type,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                cost_usd=usage.cost_usd,
                input_cost_usd=usage.input_cost_usd,
                output_cost_usd=usage.output_cost_usd,
                pipeline=usage.pipeline,
                content_id=usage.content_id,
                operation=usage.operation,
                latency_ms=usage.latency_ms,
                success=usage.success,
                error_message=usage.error_message,
            )
            session.add(log_entry)
            await session.flush()

            logger.debug(
                f"Logged LLM usage: {usage.model} - "
                f"${usage.cost_usd or 0:.4f} - {usage.operation or 'unknown'}"
            )

            return log_entry

        if session:
            return await _log(session)
        else:
            async with async_session_maker() as session:
                result = await _log(session)
                await session.commit()
                return result

    @staticmethod
    async def log_usages_batch(
        usages: list[LLMUsage], session: Optional[AsyncSession] = None
    ) -> list[LLMUsageLog]:
        """
        Log multiple LLM usage records in a single transaction.

        More efficient than calling log_usage multiple times
        for batch operations like processing a multi-page document.

        Args:
            usages: List of LLMUsage dataclasses
            session: Optional existing database session

        Returns:
            List of created LLMUsageLog records
        """

        async def _log_batch(session: AsyncSession) -> list[LLMUsageLog]:
            entries = []
            total_cost = 0.0

            for usage in usages:
                log_entry = LLMUsageLog(
                    request_id=usage.request_id,
                    model=usage.model,
                    provider=usage.provider,
                    request_type=usage.request_type,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    cost_usd=usage.cost_usd,
                    input_cost_usd=usage.input_cost_usd,
                    output_cost_usd=usage.output_cost_usd,
                    pipeline=usage.pipeline,
                    content_id=usage.content_id,
                    operation=usage.operation,
                    latency_ms=usage.latency_ms,
                    success=usage.success,
                    error_message=usage.error_message,
                )
                session.add(log_entry)
                entries.append(log_entry)
                total_cost += usage.cost_usd or 0.0

            await session.flush()

            logger.info(
                f"Logged {len(entries)} LLM usages - " f"Total cost: ${total_cost:.4f}"
            )

            return entries

        if session:
            return await _log_batch(session)
        else:
            async with async_session_maker() as session:
                result = await _log_batch(session)
                await session.commit()
                return result

    @staticmethod
    async def get_daily_cost(
        date: Optional[datetime] = None, session: Optional[AsyncSession] = None
    ) -> dict:
        """
        Get total cost for a specific day.

        Args:
            date: Date to query (defaults to today)
            session: Optional database session

        Returns:
            Dict with total_cost, request_count, and breakdown by model
        """
        if date is None:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        async def _query(session: AsyncSession) -> dict:
            # Total cost and count
            totals = await session.execute(
                select(
                    func.sum(LLMUsageLog.cost_usd).label("total_cost"),
                    func.count(LLMUsageLog.id).label("request_count"),
                    func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
                ).where(
                    LLMUsageLog.created_at >= start_of_day,
                    LLMUsageLog.created_at < end_of_day,
                )
            )
            total_row = totals.first()

            # Breakdown by model
            model_breakdown = await session.execute(
                select(
                    LLMUsageLog.model,
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                    func.count(LLMUsageLog.id).label("count"),
                )
                .where(
                    LLMUsageLog.created_at >= start_of_day,
                    LLMUsageLog.created_at < end_of_day,
                )
                .group_by(LLMUsageLog.model)
            )

            by_model = {
                row.model: {"cost": row.cost or 0, "count": row.count}
                for row in model_breakdown
            }

            # Breakdown by pipeline
            pipeline_breakdown = await session.execute(
                select(
                    LLMUsageLog.pipeline,
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                    func.count(LLMUsageLog.id).label("count"),
                )
                .where(
                    LLMUsageLog.created_at >= start_of_day,
                    LLMUsageLog.created_at < end_of_day,
                    LLMUsageLog.pipeline.isnot(None),
                )
                .group_by(LLMUsageLog.pipeline)
            )

            by_pipeline = {
                row.pipeline: {"cost": row.cost or 0, "count": row.count}
                for row in pipeline_breakdown
            }

            return {
                "date": start_of_day.isoformat(),
                "total_cost_usd": total_row.total_cost or 0,
                "request_count": total_row.request_count or 0,
                "total_tokens": total_row.total_tokens or 0,
                "by_model": by_model,
                "by_pipeline": by_pipeline,
            }

        if session:
            return await _query(session)
        else:
            async with async_session_maker() as session:
                return await _query(session)

    @staticmethod
    async def get_monthly_cost(
        year: Optional[int] = None,
        month: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        Get total cost for a specific month.

        Args:
            year: Year (defaults to current year)
            month: Month (defaults to current month)
            session: Optional database session

        Returns:
            Dict with total_cost, request_count, and daily breakdown
        """
        now = datetime.utcnow()
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1)
        else:
            end_of_month = datetime(year, month + 1, 1)

        async def _query(session: AsyncSession) -> dict:
            # Total cost and count
            totals = await session.execute(
                select(
                    func.sum(LLMUsageLog.cost_usd).label("total_cost"),
                    func.count(LLMUsageLog.id).label("request_count"),
                    func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
                ).where(
                    LLMUsageLog.created_at >= start_of_month,
                    LLMUsageLog.created_at < end_of_month,
                )
            )
            total_row = totals.first()

            # Daily breakdown
            daily_breakdown = await session.execute(
                select(
                    func.date(LLMUsageLog.created_at).label("date"),
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                    func.count(LLMUsageLog.id).label("count"),
                )
                .where(
                    LLMUsageLog.created_at >= start_of_month,
                    LLMUsageLog.created_at < end_of_month,
                )
                .group_by(func.date(LLMUsageLog.created_at))
                .order_by("date")
            )

            by_day = [
                {
                    "date": str(row.date),
                    "cost": row.cost or 0,
                    "count": row.count,
                }
                for row in daily_breakdown
            ]

            # Breakdown by model
            model_breakdown = await session.execute(
                select(
                    LLMUsageLog.model,
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                    func.count(LLMUsageLog.id).label("count"),
                )
                .where(
                    LLMUsageLog.created_at >= start_of_month,
                    LLMUsageLog.created_at < end_of_month,
                )
                .group_by(LLMUsageLog.model)
            )

            by_model = {
                row.model: {"cost": row.cost or 0, "count": row.count}
                for row in model_breakdown
            }

            return {
                "year": year,
                "month": month,
                "total_cost_usd": total_row.total_cost or 0,
                "request_count": total_row.request_count or 0,
                "total_tokens": total_row.total_tokens or 0,
                "by_day": by_day,
                "by_model": by_model,
            }

        if session:
            return await _query(session)
        else:
            async with async_session_maker() as session:
                return await _query(session)

    @staticmethod
    async def get_content_cost(
        content_id: int, session: Optional[AsyncSession] = None
    ) -> dict:
        """
        Get total LLM cost for processing a specific content item.

        Args:
            content_id: Content ID to query
            session: Optional database session

        Returns:
            Dict with total_cost and breakdown by operation
        """

        async def _query(session: AsyncSession) -> dict:
            # Total cost
            totals = await session.execute(
                select(
                    func.sum(LLMUsageLog.cost_usd).label("total_cost"),
                    func.count(LLMUsageLog.id).label("request_count"),
                    func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
                ).where(LLMUsageLog.content_id == content_id)
            )
            total_row = totals.first()

            # Breakdown by operation
            operation_breakdown = await session.execute(
                select(
                    LLMUsageLog.operation,
                    LLMUsageLog.model,
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                    func.count(LLMUsageLog.id).label("count"),
                )
                .where(LLMUsageLog.content_id == content_id)
                .group_by(LLMUsageLog.operation, LLMUsageLog.model)
            )

            by_operation = [
                {
                    "operation": row.operation,
                    "model": row.model,
                    "cost": row.cost or 0,
                    "count": row.count,
                }
                for row in operation_breakdown
            ]

            return {
                "content_id": content_id,
                "total_cost_usd": total_row.total_cost or 0,
                "request_count": total_row.request_count or 0,
                "total_tokens": total_row.total_tokens or 0,
                "by_operation": by_operation,
            }

        if session:
            return await _query(session)
        else:
            async with async_session_maker() as session:
                return await _query(session)

    @staticmethod
    async def check_budget_limit(
        limit_usd: float,
        period: str = "monthly",
        session: Optional[AsyncSession] = None,
    ) -> dict:
        """
        Check if current spend is within budget limit.

        Args:
            limit_usd: Budget limit in USD
            period: "daily" or "monthly"
            session: Optional database session

        Returns:
            Dict with current_spend, limit, remaining, and is_over_budget
        """
        if period == "daily":
            summary = await CostTracker.get_daily_cost(session=session)
            current_spend = summary["total_cost_usd"]
        else:  # monthly
            summary = await CostTracker.get_monthly_cost(session=session)
            current_spend = summary["total_cost_usd"]

        remaining = limit_usd - current_spend
        is_over_budget = current_spend > limit_usd
        percentage_used = (current_spend / limit_usd * 100) if limit_usd > 0 else 0

        result = {
            "period": period,
            "current_spend_usd": current_spend,
            "limit_usd": limit_usd,
            "remaining_usd": max(0, remaining),
            "percentage_used": percentage_used,
            "is_over_budget": is_over_budget,
        }

        # Log warning if approaching or over budget
        if is_over_budget:
            logger.warning(
                f"BUDGET EXCEEDED: {period} spend ${current_spend:.2f} "
                f"exceeds limit ${limit_usd:.2f}"
            )
        elif percentage_used >= 80:
            logger.warning(
                f"Budget alert: {period} spend at {percentage_used:.1f}% "
                f"(${current_spend:.2f} of ${limit_usd:.2f})"
            )

        return result

    @staticmethod
    async def update_cost_summary(
        period_type: str = "daily", session: Optional[AsyncSession] = None
    ) -> LLMCostSummary:
        """
        Update or create aggregated cost summary for reporting.

        Called periodically to pre-aggregate costs for fast dashboard queries.

        Args:
            period_type: "daily" or "monthly"
            session: Optional database session

        Returns:
            Updated LLMCostSummary record
        """
        now = datetime.utcnow()

        if period_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        else:  # monthly
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                period_end = datetime(now.year + 1, 1, 1)
            else:
                period_end = datetime(now.year, now.month + 1, 1)

        async def _update(session: AsyncSession) -> LLMCostSummary:
            # Get aggregated data
            totals = await session.execute(
                select(
                    func.sum(LLMUsageLog.cost_usd).label("total_cost"),
                    func.count(LLMUsageLog.id).label("request_count"),
                    func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
                ).where(
                    LLMUsageLog.created_at >= period_start,
                    LLMUsageLog.created_at < period_end,
                )
            )
            total_row = totals.first()

            # Cost by model
            model_costs = await session.execute(
                select(
                    LLMUsageLog.model,
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                )
                .where(
                    LLMUsageLog.created_at >= period_start,
                    LLMUsageLog.created_at < period_end,
                )
                .group_by(LLMUsageLog.model)
            )
            cost_by_model = {row.model: row.cost or 0 for row in model_costs}

            # Cost by pipeline
            pipeline_costs = await session.execute(
                select(
                    LLMUsageLog.pipeline,
                    func.sum(LLMUsageLog.cost_usd).label("cost"),
                )
                .where(
                    LLMUsageLog.created_at >= period_start,
                    LLMUsageLog.created_at < period_end,
                    LLMUsageLog.pipeline.isnot(None),
                )
                .group_by(LLMUsageLog.pipeline)
            )
            cost_by_pipeline = {row.pipeline: row.cost or 0 for row in pipeline_costs}

            # Find or create summary
            existing = await session.execute(
                select(LLMCostSummary).where(
                    LLMCostSummary.period_type == period_type,
                    LLMCostSummary.period_start == period_start,
                )
            )
            summary = existing.scalar_one_or_none()

            if summary:
                summary.total_cost_usd = total_row.total_cost or 0
                summary.total_requests = total_row.request_count or 0
                summary.total_tokens = total_row.total_tokens or 0
                summary.cost_by_model = cost_by_model
                summary.cost_by_pipeline = cost_by_pipeline
            else:
                summary = LLMCostSummary(
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    total_cost_usd=total_row.total_cost or 0,
                    total_requests=total_row.request_count or 0,
                    total_tokens=total_row.total_tokens or 0,
                    cost_by_model=cost_by_model,
                    cost_by_pipeline=cost_by_pipeline,
                )
                session.add(summary)

            await session.flush()
            return summary

        if session:
            return await _update(session)
        else:
            async with async_session_maker() as session:
                result = await _update(session)
                await session.commit()
                return result
