# Changelog

All notable changes to Second Brain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open-source release preparation
- Comprehensive production deployment documentation (`docs/deployment/production.md`)
- Security hardening guide (`docs/deployment/security.md`)
- Contributing guidelines (`CONTRIBUTING.md`)
- MIT License
- GitHub issue and PR templates

### Changed
- CORS configuration now uses environment variable (`CORS_ORIGINS`)
- Upload directory uses cross-platform temp directory by default
- Standardized datetime usage to timezone-aware `datetime.now(timezone.utc)`
- Standardized error handling across all API routers with shared decorator
- Improved code organization by splitting large service files

### Fixed
- N+1 query performance issue in mastery service topic states
- Incomplete TODO implementations (cleanup_old_tasks, check_duplicate)
- Magic numbers replaced with named constants throughout backend

### Security
- CORS wildcard no longer default in production (configurable via `CORS_ORIGINS`)
- Added security documentation with hardening checklist

## [0.1.0] - 2026-01-27

### Added
- **Content Ingestion**: Multi-source content capture
  - Web article extraction with Raindrop.io sync
  - PDF document processing with annotation extraction
  - Book OCR pipeline using Mistral/Gemini vision models
  - Voice memo transcription
  - GitHub repository imports
  - Quick capture (text, URL, idea, code snippets)
  
- **LLM Processing Pipeline**: AI-powered content analysis
  - Concept extraction and knowledge graph building
  - Auto-tagging with hierarchical taxonomy
  - Summary generation
  - Mastery question generation
  - Follow-up task suggestions

- **Knowledge Hub (Obsidian Integration)**
  - Automatic note generation from processed content
  - Concept notes with bidirectional linking
  - Template-based formatting (13 content types)
  - Frontmatter with structured metadata
  - Vault file watching for external changes

- **Knowledge Graph (Neo4j)**
  - Content-to-concept relationships
  - Concept-to-concept connections
  - Graph visualization with filtering
  - Relationship type support (relates_to, requires, extends, etc.)

- **Learning System**
  - Spaced repetition with SM-2 algorithm
  - Multiple card types (basic, cloze, code)
  - Practice exercises with code sandbox
  - LLM-based answer evaluation
  - Mastery tracking per topic
  - Practice streaks and time tracking

- **AI Assistant**
  - Conversational interface with RAG
  - Tool calling for knowledge operations
  - Context-aware responses
  - Conversation history

- **Analytics Dashboard**
  - Learning progress visualization
  - Topic mastery heatmaps
  - LLM usage tracking and cost attribution
  - Activity streaks and milestones

- **Mobile Capture PWA**
  - Installable progressive web app
  - Offline support with service worker
  - Quick capture for ideas on the go

### Technical
- FastAPI backend with async SQLAlchemy
- React frontend with Vite, Tailwind CSS, and Zustand
- PostgreSQL for relational data
- Redis for caching and Celery task queue
- Neo4j for knowledge graph
- Docker Compose for development environment
- Multi-LLM support (Gemini, Mistral, OpenAI, Anthropic)

---

## Version History Guidelines

When updating this changelog:

1. **Add entries under [Unreleased]** during development
2. **Move entries to a versioned section** when releasing
3. **Use semantic versioning**:
   - MAJOR: Breaking changes
   - MINOR: New features (backward compatible)
   - PATCH: Bug fixes (backward compatible)

### Entry Types

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Features to be removed in future
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security-related changes

[Unreleased]: https://github.com/your-username/second-brain/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-username/second-brain/releases/tag/v0.1.0
