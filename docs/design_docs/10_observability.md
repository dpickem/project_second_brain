# LLM Observability: Monitoring and Cost Tracking

> **Document Status**: Design Specification  
> **Last Updated**: January 2026  
> **Related Docs**: 02_llm_processing_layer.md, 06_backend_api.md

---

## 1. Executive Summary

This document describes the observability strategy for LLM operations in Second Brain. We currently use a custom cost tracking system built on LiteLLM and PostgreSQL. This document evaluates whether adding Langfuse would provide meaningful benefits.

**Recommendation**: Keep the current custom implementation for cost tracking, but consider Langfuse for development/debugging workflows where trace visualization would accelerate iteration.

---

## 2. Current Implementation

### 2.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LLM CALL FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pipeline/Service                                               │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐                                                │
│  │ LLMClient   │ ◄── Wraps LiteLLM with cost tracking           │
│  │ (client.py) │                                                │
│  └──────┬──────┘                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐     ┌─────────────────────────────────────┐    │
│  │  LiteLLM    │────►│ OpenAI / Anthropic / Gemini / etc.  │    │
│  └──────┬──────┘     └─────────────────────────────────────┘    │
│         │                                                       │
│         ▼ (returns LLMUsage)                                    │
│  ┌─────────────┐                                                │
│  │CostTracker  │ ◄── Batches & persists usage records           │
│  └──────┬──────┘                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    PostgreSQL                            │    │
│  │  ┌─────────────────┐    ┌───────────────────────────┐   │    │
│  │  │ llm_usage_logs  │    │ llm_cost_summaries        │   │    │
│  │  │                 │    │                           │   │    │
│  │  │ • request_id    │    │ • date                    │   │    │
│  │  │ • model         │    │ • total_cost_usd          │   │    │
│  │  │ • tokens        │    │ • total_requests          │   │    │
│  │  │ • cost_usd      │    │ • by_model (JSON)         │   │    │
│  │  │ • pipeline      │    │ • by_pipeline (JSON)      │   │    │
│  │  │ • operation     │    └───────────────────────────┘   │    │
│  │  │ • content_id    │                                    │    │
│  │  │ • latency_ms    │                                    │    │
│  │  └─────────────────┘                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 What We Track

| Field | Description |
|-------|-------------|
| `request_id` | Unique identifier for each LLM call |
| `model` | Model identifier (e.g., `gemini/gemini-3-flash-preview`) |
| `provider` | Provider name (`openai`, `anthropic`, `gemini`) |
| `pipeline` | Which pipeline made the call (`RAINDROP_SYNC`, `PDF_PROCESSOR`) |
| `operation` | Specific operation (`SUMMARIZATION`, `EXTRACTION`, `OCR`) |
| `content_id` | Links cost to specific content item |
| `prompt_tokens` | Input token count |
| `completion_tokens` | Output token count |
| `cost_usd` | Calculated cost using LiteLLM's pricing |
| `latency_ms` | Request duration |
| `success` | Whether the call succeeded |
| `error_message` | Error details if failed |

### 2.3 Capabilities

**Cost Management:**
- Real-time cost tracking per request
- Daily/monthly cost summaries
- Cost attribution by pipeline, model, content
- Budget alerts (configurable thresholds)

**Reporting:**
- API endpoints for cost analytics (`/api/analytics/llm-costs`)
- Historical cost trends
- Model comparison (cost per operation type)

**Limitations:**
- No trace visualization (can't see prompt→response flow)
- No prompt versioning or A/B testing
- No real-time streaming dashboard
- Manual SQL queries for deep analysis

---

## 3. Langfuse Evaluation

### 3.1 What is Langfuse?

[Langfuse](https://langfuse.com/) is an open-source LLM observability platform that provides:

- **Tracing**: Visualize full LLM call chains with inputs/outputs
- **Prompt Management**: Version and A/B test prompts
- **Evaluations**: Run automated quality checks on outputs
- **Analytics**: Cost, latency, and quality dashboards
- **Self-hostable**: Can run locally or use cloud

### 3.2 LiteLLM + Langfuse Integration

Langfuse has first-class LiteLLM integration via callbacks:

```python
from litellm import completion
from langfuse import Langfuse

langfuse = Langfuse()

# Automatic tracing via callback
response = completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
    metadata={"langfuse_trace_id": "my-trace"},
)
```

Or via the LiteLLM proxy with Langfuse callback enabled.

### 3.3 Feature Comparison

| Feature | Current (Custom) | Langfuse |
|---------|-----------------|----------|
| **Cost Tracking** | ✅ Full | ✅ Full |
| **Token Counting** | ✅ Via LiteLLM | ✅ Via LiteLLM |
| **Per-Content Attribution** | ✅ Native FK to content | ⚠️ Via metadata tags |
| **Trace Visualization** | ❌ None | ✅ Full trace UI |
| **Prompt/Response Logging** | ❌ Not stored | ✅ Full history |
| **Prompt Versioning** | ❌ None | ✅ Built-in |
| **Latency Analytics** | ✅ Basic (per-request) | ✅ Rich dashboards |
| **Real-time Dashboard** | ❌ None | ✅ Yes |
| **Data Ownership** | ✅ PostgreSQL | ✅ Self-host or cloud |
| **Offline Access** | ✅ Always | ⚠️ Requires running server |
| **Query Flexibility** | ✅ Full SQL | ⚠️ Limited to UI/API |
| **Setup Complexity** | ✅ None (built-in) | ⚠️ Additional service |

### 3.4 When Langfuse Adds Value

**Good for:**
1. **Debugging complex chains**: When a multi-step pipeline fails, trace visualization helps pinpoint which step broke
2. **Prompt iteration**: See exactly what prompts produce what outputs during development
3. **Quality evaluation**: Score outputs and track quality over time
4. **Team collaboration**: Share traces with others for review

**Not needed for:**
1. **Cost tracking**: We already have this
2. **Simple pipelines**: Single-shot LLM calls don't benefit from tracing
3. **Production monitoring**: Our custom logs suffice for alerting

---

## 4. Recommendation

### 4.1 Keep Current Implementation

The custom `CostTracker` + PostgreSQL approach should remain the **primary** observability system because:

1. **Data ownership**: All data stays in our PostgreSQL database
2. **Query flexibility**: Full SQL access for custom reports
3. **Content attribution**: Native foreign key to content items
4. **No external dependencies**: Works offline, no additional services
5. **Already working**: Proven in production

### 4.2 Consider Langfuse for Development

Langfuse could be valuable as an **optional development tool**:

```yaml
# docker-compose.override.yml (local dev only)
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://...
```

**Use cases:**
- Debugging failing pipelines during development
- Iterating on prompt engineering
- Onboarding new contributors (visual understanding)

### 4.3 Implementation Path (If Adopted)

**Phase 1: Optional Development Mode**
```python
# In settings.py
LANGFUSE_ENABLED: bool = False  # Only enable locally
LANGFUSE_HOST: str = "http://localhost:3001"
```

**Phase 2: Dual-Write (Development)**
```python
# In LLMClient
if settings.LANGFUSE_ENABLED:
    # Also send to Langfuse for trace visualization
    langfuse.trace(...)

# Always write to PostgreSQL (source of truth)
await CostTracker.log_usage(usage)
```

**Phase 3: Evaluate Value**
- After 1-2 months, assess if trace visualization is actually used
- If valuable, consider keeping; if not, remove

---

## 5. API Endpoints

Current observability endpoints (no changes needed):

| Endpoint | Description |
|----------|-------------|
| `GET /api/analytics/llm-costs` | Cost summary for date range |
| `GET /api/analytics/llm-costs/by-model` | Breakdown by model |
| `GET /api/analytics/llm-costs/by-pipeline` | Breakdown by pipeline |
| `GET /api/analytics/llm-costs/by-content/{id}` | Cost for specific content |

---

## 6. Database Schema

### Current Schema (Sufficient)

```sql
-- Individual LLM calls
CREATE TABLE llm_usage_logs (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255),
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50),
    request_type VARCHAR(50),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd FLOAT,
    pipeline pipeline_name,
    content_uuid VARCHAR(36),
    db_content_id INTEGER REFERENCES content(id),
    operation pipeline_operation,
    latency_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily aggregations (for fast queries)
CREATE TABLE llm_cost_summaries (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_cost_usd FLOAT NOT NULL,
    total_requests INTEGER NOT NULL,
    total_tokens INTEGER,
    by_model JSONB,
    by_pipeline JSONB,
    by_operation JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 7. Conclusion

The current observability system is **sufficient for production needs**. Langfuse would add value primarily during development for trace visualization and prompt iteration, but the complexity of running an additional service may not be worth it for a single-developer project.

**Decision**: Keep current implementation. Re-evaluate Langfuse if:
- Multi-step agent workflows are added (where tracing becomes essential)
- Team grows and needs shared visibility into LLM behavior
- Prompt engineering becomes a significant time investment
