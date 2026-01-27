# Production Deployment Guide

This guide covers deploying Second Brain to a production environment with proper security, SSL/TLS, and reverse proxy configuration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Server Setup](#server-setup)
- [Docker Production Configuration](#docker-production-configuration)
- [SSL/TLS with Let's Encrypt](#ssltls-with-lets-encrypt)
- [Nginx Reverse Proxy](#nginx-reverse-proxy)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Backup and Restore](#backup-and-restore)
- [Monitoring](#monitoring)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB SSD | 100+ GB SSD |
| Network | 100 Mbps | 1 Gbps |

### Software Requirements

- Linux server (Ubuntu 22.04 LTS recommended)
- Docker 24.0+ and Docker Compose 2.20+
- Nginx (for reverse proxy)
- Certbot (for SSL certificates)
- Domain name with DNS configured

### Network Requirements

- Ports 80/443 open for HTTP/HTTPS traffic
- Outbound access for LLM API calls (OpenAI, Anthropic, Mistral, etc.)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Internet                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │   Nginx     │  (Reverse Proxy + SSL)
                    │  :80/:443   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐   ┌──────┴──────┐   ┌─────┴─────┐
    │ Frontend  │   │   Backend   │   │  Capture  │
    │   :3000   │   │    :8000    │   │ PWA :5174 │
    └───────────┘   └──────┬──────┘   └───────────┘
                           │
       ┌───────────┬───────┼───────┬───────────┐
       │           │       │       │           │
  ┌────┴────┐ ┌────┴────┐ ┌┴────┐ ┌┴─────┐ ┌───┴───┐
  │Postgres │ │  Neo4j  │ │Redis│ │Worker│ │Worker │
  │ :5432   │ │  :7687  │ │:6379│ │  #1  │ │  #2   │
  └─────────┘ └─────────┘ └─────┘ └──────┘ └───────┘
```

In production:
- Nginx terminates SSL and proxies requests to internal services
- Database ports (5432, 6379, 7474, 7687) are NOT exposed to the internet
- Only Nginx ports 80/443 are publicly accessible

---

## Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw
```

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### 3. Configure Firewall

```bash
# Allow SSH, HTTP, HTTPS only
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 4. Create Application User

```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash secondbrain
sudo usermod -aG docker secondbrain

# Create data directory
sudo mkdir -p /opt/secondbrain/data
sudo chown -R secondbrain:secondbrain /opt/secondbrain
```

---

## Docker Production Configuration

### 1. Clone Repository

```bash
sudo -u secondbrain -i
cd /opt/secondbrain
git clone https://github.com/yourusername/project_second_brain.git app
cd app
```

### 2. Create Production Override

Create `docker-compose.prod.yml` to override development settings:

```yaml
# docker-compose.prod.yml
# Production overrides - use with: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

services:
  # =============================================================================
  # PostgreSQL - Remove port exposure, add resource limits
  # =============================================================================
  postgres:
    ports: []  # Don't expose to host
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped

  # =============================================================================
  # Redis - Remove port exposure, add resource limits
  # =============================================================================
  redis:
    ports: []  # Don't expose to host
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    restart: unless-stopped

  # =============================================================================
  # Neo4j - Remove port exposure, add resource limits
  # =============================================================================
  neo4j:
    ports: []  # Don't expose to host
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:?NEO4J_PASSWORD is required}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=1G
      - NEO4J_dbms_memory_pagecache_size=512m
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    restart: unless-stopped

  # =============================================================================
  # Backend - Production settings
  # =============================================================================
  backend:
    ports: []  # Nginx will proxy to this
    environment:
      DEBUG: "false"
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    restart: unless-stopped
    # Expose on internal network for Nginx
    networks:
      - default
      - nginx-proxy

  # =============================================================================
  # Celery Workers - Production settings
  # =============================================================================
  celery-worker-1:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: unless-stopped

  celery-worker-2:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: unless-stopped

  # =============================================================================
  # Frontend - Production build
  # =============================================================================
  frontend:
    ports: []  # Nginx will proxy to this
    command: npm run build && npx serve -s dist -l 3000
    volumes: []  # Don't mount source in production
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped
    networks:
      - default
      - nginx-proxy

  # =============================================================================
  # Capture PWA - Production build
  # =============================================================================
  capture-pwa:
    ports: []  # Nginx will proxy to this
    volumes: []  # Don't mount source in production
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
    restart: unless-stopped
    networks:
      - default
      - nginx-proxy

networks:
  nginx-proxy:
    external: true
```

### 3. Create Production Environment File

```bash
cp .env.example .env
chmod 600 .env  # Restrict permissions
```

Edit `.env` with production values (see [Environment Configuration](#environment-configuration)).

---

## SSL/TLS with Let's Encrypt

### 1. Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Obtain Certificate

```bash
# Replace with your domain
sudo certbot certonly --nginx -d secondbrain.yourdomain.com

# Verify certificate
sudo certbot certificates
```

### 3. Auto-Renewal

Certbot automatically configures a systemd timer. Verify:

```bash
sudo systemctl status certbot.timer
```

---

## Nginx Reverse Proxy

### 1. Install Nginx

```bash
sudo apt install -y nginx
```

### 2. Create Configuration

Create `/etc/nginx/sites-available/secondbrain`:

```nginx
# /etc/nginx/sites-available/secondbrain
# Second Brain - Nginx Reverse Proxy Configuration

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;

# Upstream definitions
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:3000;
    keepalive 16;
}

upstream capture {
    server 127.0.0.1:5174;
    keepalive 16;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name secondbrain.yourdomain.com;
    
    # Allow Let's Encrypt challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name secondbrain.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/secondbrain.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/secondbrain.yourdomain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/secondbrain.access.log;
    error_log /var/log/nginx/secondbrain.error.log;

    # Client body size (for file uploads)
    client_max_body_size 100M;

    # ==========================================================================
    # API Backend
    # ==========================================================================
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        
        # Timeouts for long-running operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check endpoint (no rate limit)
    location /api/health {
        proxy_pass http://backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # ==========================================================================
    # Capture PWA (mobile app)
    # ==========================================================================
    location /capture/ {
        limit_req zone=general burst=50 nodelay;
        
        proxy_pass http://capture/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # ==========================================================================
    # Main Frontend
    # ==========================================================================
    location / {
        limit_req zone=general burst=50 nodelay;
        
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # ==========================================================================
    # Static assets caching
    # ==========================================================================
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        proxy_pass http://frontend;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. Enable Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/secondbrain /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## Environment Configuration

Production `.env` should include:

```bash
# =============================================================================
# PRODUCTION ENVIRONMENT FILE
# =============================================================================

# Data directory (use absolute path)
DATA_DIR=/opt/secondbrain/data

# PostgreSQL (use strong passwords!)
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=<generate-32-char-random-password>
POSTGRES_DB=secondbrain

# Neo4j
NEO4J_PASSWORD=<generate-32-char-random-password>

# Obsidian vault path (inside container)
OBSIDIAN_VAULT_PATH=/vault

# LLM API Keys
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...

# Model configuration
OCR_MODEL=mistral/mistral-ocr-2512
TEXT_MODEL=gemini/gemini-3-flash-preview

# Cost budget
LITELLM_BUDGET_MAX=100.0
LITELLM_BUDGET_ALERT=80.0

# CORS - specify your domain
CORS_ORIGINS=https://secondbrain.yourdomain.com

# Capture API authentication
CAPTURE_API_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32)">

# Debug off in production
DEBUG=false

# Frontend URL (for CORS and redirects)
VITE_API_URL=https://secondbrain.yourdomain.com/api
VITE_CAPTURE_API_KEY=<same-as-CAPTURE_API_KEY>
```

### Generate Secure Passwords

```bash
# Generate random passwords
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Database Setup

### 1. Initial Setup

```bash
cd /opt/secondbrain/app

# Start databases first
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres redis neo4j

# Wait for health checks
sleep 30

# Run migrations
docker compose exec backend alembic upgrade head
```

### 2. Start All Services

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Backup and Restore

### PostgreSQL Backup

#### Create Backup Script

Create `/opt/secondbrain/scripts/backup-postgres.sh`:

```bash
#!/bin/bash
# PostgreSQL backup script

set -e

# Configuration
BACKUP_DIR="/opt/secondbrain/backups/postgres"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Load environment
source /opt/secondbrain/app/.env

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup
docker exec project_second_brain-postgres-1 \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Delete old backups
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR/backup_$DATE.sql.gz"
```

#### Schedule Daily Backups

```bash
# Make executable
chmod +x /opt/secondbrain/scripts/backup-postgres.sh

# Add to crontab (runs at 2 AM daily)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/secondbrain/scripts/backup-postgres.sh >> /var/log/secondbrain-backup.log 2>&1") | crontab -
```

#### Restore from Backup

```bash
# Stop services
docker compose down

# Restore
gunzip -c /opt/secondbrain/backups/postgres/backup_YYYYMMDD_HHMMSS.sql.gz \
    | docker exec -i project_second_brain-postgres-1 \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Restart services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Neo4j Backup

#### Create Backup Script

Create `/opt/secondbrain/scripts/backup-neo4j.sh`:

```bash
#!/bin/bash
# Neo4j backup script

set -e

BACKUP_DIR="/opt/secondbrain/backups/neo4j"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Stop Neo4j for consistent backup
docker compose stop neo4j

# Copy data directory
tar -czf "$BACKUP_DIR/neo4j_$DATE.tar.gz" \
    -C /opt/secondbrain/data neo4j

# Restart Neo4j
docker compose start neo4j

# Delete old backups
find "$BACKUP_DIR" -name "neo4j_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Neo4j backup completed: $BACKUP_DIR/neo4j_$DATE.tar.gz"
```

### Obsidian Vault Backup

```bash
#!/bin/bash
# Obsidian vault backup script

set -e

BACKUP_DIR="/opt/secondbrain/backups/vault"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Create backup
tar -czf "$BACKUP_DIR/vault_$DATE.tar.gz" \
    -C /opt/secondbrain/data obsidian

# Delete old backups
find "$BACKUP_DIR" -name "vault_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Vault backup completed: $BACKUP_DIR/vault_$DATE.tar.gz"
```

### Automated Full Backup

Create `/opt/secondbrain/scripts/backup-all.sh`:

```bash
#!/bin/bash
# Full backup script - runs all individual backups

set -e

SCRIPT_DIR="/opt/secondbrain/scripts"

echo "Starting full backup at $(date)"

$SCRIPT_DIR/backup-postgres.sh
$SCRIPT_DIR/backup-neo4j.sh
$SCRIPT_DIR/backup-vault.sh

echo "Full backup completed at $(date)"
```

---

## Monitoring

### Docker Health Checks

```bash
# Check all container status
docker compose ps

# Check container health
docker inspect --format='{{.State.Health.Status}}' project_second_brain-postgres-1
docker inspect --format='{{.State.Health.Status}}' project_second_brain-redis-1
docker inspect --format='{{.State.Health.Status}}' project_second_brain-neo4j-1

# View logs
docker compose logs -f --tail=100
```

### Health Endpoint

The backend provides a health endpoint at `/health`:

```bash
curl https://secondbrain.yourdomain.com/api/health
```

### Log Rotation

Add to `/etc/logrotate.d/secondbrain`:

```
/var/log/nginx/secondbrain.*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

### Basic Monitoring Script

Create `/opt/secondbrain/scripts/health-check.sh`:

```bash
#!/bin/bash
# Simple health check script

HEALTH_URL="http://localhost:8000/health"
ALERT_EMAIL="admin@yourdomain.com"

response=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$response" != "200" ]; then
    echo "Health check failed at $(date). Status: $response" | \
        mail -s "Second Brain Health Alert" "$ALERT_EMAIL"
fi
```

---

## Maintenance

### Update Application

```bash
cd /opt/secondbrain/app

# Pull latest changes
git pull

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Run any new migrations
docker compose exec backend alembic upgrade head
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery-worker-1 celery-worker-2

# Last 100 lines
docker compose logs --tail=100 backend
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart

# Restart specific service
docker compose restart backend
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (careful!)
docker volume prune

# Remove build cache
docker builder prune
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Refused

```bash
# Check if databases are running
docker compose ps

# Check database logs
docker compose logs postgres
docker compose logs neo4j

# Verify network connectivity
docker compose exec backend ping postgres
```

#### 2. 502 Bad Gateway

```bash
# Check if backend is running
docker compose ps backend

# Check backend logs
docker compose logs backend

# Check Nginx logs
sudo tail -f /var/log/nginx/secondbrain.error.log
```

#### 3. SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew manually if needed
sudo certbot renew --dry-run
sudo certbot renew
```

#### 4. Out of Disk Space

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up
docker system prune -a --volumes
```

#### 5. Memory Issues

```bash
# Check memory usage
free -h
docker stats

# Reduce container memory limits in docker-compose.prod.yml
```

### Debug Mode

To enable debug mode temporarily:

```bash
# Edit .env
DEBUG=true

# Restart backend
docker compose restart backend

# View detailed logs
docker compose logs -f backend

# Don't forget to disable after debugging!
```

### Database Shell Access

```bash
# PostgreSQL
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB

# Redis
docker compose exec redis redis-cli

# Neo4j (via HTTP)
curl -u neo4j:$NEO4J_PASSWORD http://localhost:7474/db/neo4j/tx/commit \
    -H "Content-Type: application/json" \
    -d '{"statements": [{"statement": "MATCH (n) RETURN count(n)"}]}'
```

---

## Next Steps

After completing this deployment:

1. **Security Hardening**: Review [Security Guide](security.md)
2. **Monitoring Setup**: Consider adding Prometheus/Grafana for metrics
3. **Backup Verification**: Test restore procedures regularly
4. **SSL Renewal**: Verify automatic certificate renewal works
5. **Update Schedule**: Plan regular maintenance windows
