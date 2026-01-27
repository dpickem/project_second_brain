# Security Hardening Guide

This guide covers security best practices for deploying Second Brain in production environments.

## Table of Contents

- [Security Checklist](#security-checklist)
- [Network Security](#network-security)
- [Authentication & Authorization](#authentication--authorization)
- [Secrets Management](#secrets-management)
- [Database Security](#database-security)
- [Container Security](#container-security)
- [API Security](#api-security)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring & Auditing](#monitoring--auditing)
- [Incident Response](#incident-response)

---

## Security Checklist

Before going to production, verify these items:

### Critical

- [ ] All default passwords changed
- [ ] Database ports not exposed to internet (5432, 6379, 7474, 7687)
- [ ] SSL/TLS enabled for all public endpoints
- [ ] `DEBUG=false` in production
- [ ] CORS restricted to specific origins
- [ ] Capture API key configured
- [ ] Firewall configured (UFW/iptables)
- [ ] `.env` file has restricted permissions (chmod 600)

### Important

- [ ] Rate limiting enabled in Nginx
- [ ] Security headers configured
- [ ] Log rotation configured
- [ ] Automated backups enabled
- [ ] Container resource limits set
- [ ] Non-root user for application

### Recommended

- [ ] Intrusion detection system (fail2ban)
- [ ] Automated security updates
- [ ] Regular dependency audits
- [ ] Penetration testing schedule

---

## Network Security

### Firewall Configuration

Only expose necessary ports to the public internet:

```bash
# Reset to default
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (consider changing default port)
sudo ufw allow ssh

# Allow HTTP/HTTPS only
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status verbose
```

### Docker Network Isolation

The production docker-compose removes port bindings from databases:

```yaml
# docker-compose.prod.yml
services:
  postgres:
    ports: []  # No external access
  
  redis:
    ports: []  # No external access
  
  neo4j:
    ports: []  # No external access
```

Services communicate via Docker's internal network.

### Fail2ban for SSH Protection

```bash
# Install
sudo apt install -y fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Edit `/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
```

Add protection for Nginx:

```ini
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/secondbrain.error.log
maxretry = 5
bantime = 3600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/secondbrain.error.log
maxretry = 10
bantime = 3600
```

---

## Authentication & Authorization

### Capture API Authentication

The Capture API uses API key authentication:

```bash
# Generate secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Set in .env
CAPTURE_API_KEY=<generated-key>
VITE_CAPTURE_API_KEY=<same-key>
```

All capture endpoints require the `X-API-Key` header:

```bash
curl -X POST https://yourdomain.com/api/capture/voice \
    -H "X-API-Key: your-api-key" \
    -F "file=@memo.m4a"
```

### Session Security

The backend uses secure session configuration. Ensure these settings:

```python
# Already configured in backend
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = "Strict"  # CSRF protection
```

### Future: User Authentication

For multi-user deployments, consider:

- OAuth 2.0 / OpenID Connect integration
- JWT tokens with short expiration
- Role-based access control (RBAC)
- MFA for admin accounts

---

## Secrets Management

### Environment Variables

**Never commit secrets to version control:**

```bash
# .gitignore already includes
.env
*.pem
*.key
```

Secure the `.env` file:

```bash
# Restrict permissions
chmod 600 /opt/secondbrain/app/.env
chown secondbrain:secondbrain /opt/secondbrain/app/.env
```

### Password Requirements

Generate strong passwords for all services:

```bash
# PostgreSQL password (32 chars)
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"

# Neo4j password (32 chars)
python3 -c "import secrets; print('NEO4J_PASSWORD=' + secrets.token_urlsafe(32))"

# Capture API key (32 chars)
python3 -c "import secrets; print('CAPTURE_API_KEY=' + secrets.token_urlsafe(32))"
```

### API Key Security

For LLM API keys:

1. **Use separate keys for development/production**
2. **Set budget limits** in provider dashboards
3. **Monitor usage** via the LLM Usage dashboard
4. **Rotate keys** periodically
5. **Use least-privilege** - only enable needed models

```bash
# Example: OpenAI API key restrictions
# In OpenAI dashboard:
# - Set monthly budget limit
# - Restrict to needed models (gpt-4o, text-embedding-3-small)
# - Enable usage notifications
```

### Secret Rotation

Establish a rotation schedule:

| Secret | Rotation Frequency |
|--------|-------------------|
| Database passwords | 90 days |
| API keys | 90 days or on suspected breach |
| SSL certificates | Auto-renewed (Let's Encrypt) |
| Capture API key | 90 days |

---

## Database Security

### PostgreSQL

#### Connection Security

PostgreSQL listens only on internal Docker network:

```yaml
# In docker-compose, no ports exposed
postgres:
  ports: []  # Internal only
```

#### Access Control

The default configuration uses password authentication. For enhanced security:

```sql
-- Connect to PostgreSQL
-- Create read-only user for analytics (optional)
CREATE ROLE readonly WITH LOGIN PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE secondbrain TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
```

#### Audit Logging

Enable query logging for security audits:

```yaml
# In docker-compose
postgres:
  command: >
    postgres
    -c log_statement=all
    -c log_connections=on
    -c log_disconnections=on
```

### Redis

Redis is used for Celery task queues. Ensure:

1. **No password by default** - acceptable since not exposed to internet
2. **No persistence of sensitive data** - only task metadata
3. **Memory limits** - prevent DoS via memory exhaustion

For enhanced security, add authentication:

```yaml
# docker-compose
redis:
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
```

### Neo4j

#### Authentication

Always use authentication in production:

```yaml
neo4j:
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
```

#### Access Control

Neo4j supports role-based access. For multi-user scenarios:

```cypher
// Create read-only user
CALL dbms.security.createUser('reader', 'password', false);
CALL dbms.security.addRoleToUser('reader', 'reader');
```

---

## Container Security

### Non-Root Execution

The backend Dockerfile could be enhanced:

```dockerfile
# Enhanced Dockerfile for production
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and change ownership
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup alembic.ini .

# Switch to non-root user
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Resource Limits

Always set resource limits in production:

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

This prevents:
- Resource exhaustion attacks
- Runaway processes
- Impact on other services

### Image Security

```bash
# Scan images for vulnerabilities
docker scout cves project_second_brain-backend

# Or use Trivy
trivy image project_second_brain-backend
```

### Read-Only File Systems

For maximum security, run containers with read-only root:

```yaml
services:
  backend:
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - /vault:/vault:rw  # Only vault needs write access
```

---

## API Security

### Rate Limiting

Nginx rate limiting is configured in the [production guide](production.md):

```nginx
# 10 requests per second for API
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ...
}
```

### Input Validation

The backend uses Pydantic for request validation:

```python
# Example from backend - all inputs are validated
class CaptureRequest(BaseModel):
    content_type: ContentType  # Enum validation
    title: str = Field(max_length=500)  # Length limits
    content: str = Field(max_length=100000)  # Size limits
```

### CORS Configuration

Restrict CORS to your domains only:

```bash
# .env
CORS_ORIGINS=https://secondbrain.yourdomain.com,https://app.yourdomain.com
```

Never use `CORS_ORIGINS=*` in production.

### Security Headers

Nginx adds security headers (configured in production.md):

```nginx
# Prevent clickjacking
add_header X-Frame-Options "SAMEORIGIN" always;

# Prevent MIME sniffing
add_header X-Content-Type-Options "nosniff" always;

# XSS protection
add_header X-XSS-Protection "1; mode=block" always;

# Referrer policy
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# Content Security Policy (add based on your needs)
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

### Request Size Limits

Prevent large payload attacks:

```nginx
# Nginx
client_max_body_size 100M;  # Match your upload limits

# Backend already validates
PDF_MAX_FILE_SIZE_MB=50
```

---

## SSL/TLS Configuration

### Modern SSL Settings

Use strong cipher configuration:

```nginx
# /etc/nginx/sites-available/secondbrain

# TLS 1.2 and 1.3 only (TLS 1.0 and 1.1 are deprecated)
ssl_protocols TLSv1.2 TLSv1.3;

# Modern cipher suite
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

# Let the client choose (modern clients have good defaults)
ssl_prefer_server_ciphers off;

# Session settings
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### HSTS (HTTP Strict Transport Security)

Force HTTPS for all future requests:

```nginx
# Add after ssl_certificate directives
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

### Test SSL Configuration

```bash
# Use SSL Labs
# https://www.ssllabs.com/ssltest/analyze.html?d=secondbrain.yourdomain.com

# Or use testssl.sh locally
docker run --rm -ti drwetter/testssl.sh https://secondbrain.yourdomain.com
```

Aim for an A+ rating.

---

## Monitoring & Auditing

### Access Logs

Configure detailed logging:

```nginx
# /etc/nginx/nginx.conf
log_format detailed '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time';

access_log /var/log/nginx/secondbrain.access.log detailed;
```

### Error Monitoring

Backend errors are logged via Python logging:

```bash
# View backend errors
docker compose logs backend | grep -i error

# View Celery worker errors
docker compose logs celery-worker-1 celery-worker-2 | grep -i error
```

### Security Event Monitoring

Monitor for suspicious activity:

```bash
# Failed authentication attempts
grep "401" /var/log/nginx/secondbrain.access.log | tail -20

# Rate limit hits
grep "limiting" /var/log/nginx/secondbrain.error.log | tail -20

# Large requests (potential DoS)
awk '$10 > 10000000' /var/log/nginx/secondbrain.access.log
```

### LLM Usage Monitoring

Monitor for unusual LLM API usage:

```bash
# Via the admin dashboard
curl https://yourdomain.com/api/llm-usage/daily-summary \
    -H "Authorization: Bearer $TOKEN"

# Check for budget alerts in logs
docker compose logs backend | grep -i "budget"
```

---

## Incident Response

### Suspected Breach Checklist

1. **Isolate**: Take affected systems offline if necessary
   ```bash
   docker compose down
   ```

2. **Preserve Evidence**: Don't modify logs
   ```bash
   cp -r /var/log/nginx /tmp/nginx-logs-backup
   docker compose logs > /tmp/docker-logs-backup.txt
   ```

3. **Rotate Credentials**: Change all passwords and API keys
   ```bash
   # Generate new secrets
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Update .env with new values
   # Restart services
   ```

4. **Review Logs**: Check for unauthorized access
   ```bash
   # Check access patterns
   grep "POST /api/capture" /var/log/nginx/secondbrain.access.log
   
   # Check for unusual IPs
   awk '{print $1}' /var/log/nginx/secondbrain.access.log | sort | uniq -c | sort -rn
   ```

5. **Notify**: Inform affected parties if data was compromised

6. **Document**: Record incident timeline and actions taken

### API Key Compromise

If an LLM API key is compromised:

1. **Rotate immediately** in provider dashboard
2. **Check usage** for unauthorized charges
3. **Update** `.env` and restart services
4. **Review** how key was exposed

### Database Compromise

If database credentials are compromised:

1. **Change passwords** immediately
2. **Review** recent database activity
3. **Restore from backup** if data was modified
4. **Audit** access logs for unauthorized connections

---

## Regular Security Tasks

### Weekly

- [ ] Review error logs for anomalies
- [ ] Check LLM usage for unexpected spikes
- [ ] Verify backup completion

### Monthly

- [ ] Update system packages: `apt update && apt upgrade`
- [ ] Review Docker images for updates
- [ ] Test backup restoration
- [ ] Review firewall rules

### Quarterly

- [ ] Rotate database passwords
- [ ] Rotate API keys
- [ ] Run vulnerability scans
- [ ] Review access patterns

### Annually

- [ ] Security audit / penetration test
- [ ] Review and update security policies
- [ ] Dependency audit for known vulnerabilities
- [ ] SSL certificate review (even with auto-renewal)

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Nginx Security Tips](https://docs.nginx.com/nginx/admin-guide/security-controls/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
