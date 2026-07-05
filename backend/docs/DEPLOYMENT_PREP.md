# Deployment Preparation

Prepared but not deployed:

- `Dockerfile`
- `docker-compose.yml`
- `scripts/init_db.py`
- `scripts/backup_db.py`
- `scripts/restore_db.py`
- `scripts/run_local.py`
- Alembic scaffold

Production hardening still needed before cloud deployment:

- Replace default `JWT_SECRET_KEY`.
- Use PostgreSQL.
- Move local storage to object storage.
- Configure HTTPS and reverse proxy.
- Configure structured logs and backups.
- Add managed secret storage.

