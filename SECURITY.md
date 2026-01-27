# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report security vulnerabilities by emailing the maintainers directly or using GitHub's private vulnerability reporting feature:

1. Go to the repository's **Security** tab
2. Click **Report a vulnerability**
3. Fill out the vulnerability report form

### What to Include

Please include the following information in your report:

- **Description**: A clear description of the vulnerability
- **Impact**: What an attacker could achieve by exploiting this vulnerability
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Affected Components**: Which parts of the system are affected (backend, frontend, etc.)
- **Suggested Fix**: If you have ideas on how to fix the issue (optional)
- **Your Contact**: How we can reach you for follow-up questions

### Response Timeline

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 7 days
- **Resolution Timeline**: We aim to resolve critical vulnerabilities within 30 days

### Disclosure Policy

- We will work with you to understand and resolve the issue
- We will keep you informed of our progress
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- We ask that you do not disclose the vulnerability publicly until we have released a fix

## Security Best Practices for Deployment

When deploying Second Brain in production, please follow these security guidelines:

### Environment Configuration

```bash
# Never use default credentials in production
POSTGRES_PASSWORD=<strong-random-password>
NEO4J_PASSWORD=<strong-random-password>
SECRET_KEY=<64-character-random-string>

# Restrict CORS to your domain
CORS_ORIGINS=https://yourdomain.com

# Use secure session settings
SESSION_SECURE=true
```

### Network Security

- Use a reverse proxy (Nginx, Traefik) with TLS termination
- Keep database ports (5432, 7474, 7687, 6379) internal only
- Enable firewall rules to restrict access
- Use Docker network isolation

### API Security

- Enable rate limiting in production
- Use HTTPS for all connections
- Validate and sanitize all user inputs
- Keep dependencies updated

### Data Protection

- Regular database backups with encryption
- Secure backup storage with limited access
- Log rotation and secure log storage

For comprehensive security guidance, see [docs/deployment/security.md](docs/deployment/security.md).

## Security Features

Second Brain includes the following security features:

- **Authentication**: Session-based authentication (configurable)
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **XSS Prevention**: React's built-in escaping for rendered content
- **CORS Configuration**: Configurable allowed origins
- **Rate Limiting**: Configurable API rate limits
- **Secrets Management**: Environment-based configuration

## Known Security Considerations

### Local-First Design

Second Brain is designed as a local-first application where:

- The Obsidian vault is stored locally
- LLM API calls are made directly to providers
- Neo4j and PostgreSQL run as local Docker containers

This design prioritizes data ownership but means:

- Users are responsible for securing their local environment
- API keys are stored in local `.env` files
- Network exposure should be carefully managed if accessible remotely

### LLM Data Considerations

Content processed through LLM providers (Gemini, Mistral, OpenAI, Anthropic) is sent to their APIs. Review each provider's data handling policies:

- [Google Gemini Privacy](https://ai.google.dev/terms)
- [Mistral AI Privacy](https://mistral.ai/terms/)
- [OpenAI Privacy](https://openai.com/policies/privacy-policy)
- [Anthropic Privacy](https://www.anthropic.com/privacy)

## Security Updates

Security updates will be released as patch versions. We recommend:

1. Watching this repository for releases
2. Regularly pulling updates
3. Reviewing the CHANGELOG for security-related changes
4. Updating dependencies periodically

## Contact

For security-related questions that are not vulnerability reports, you can open a GitHub issue with the "security" label.

Thank you for helping keep Second Brain secure!
