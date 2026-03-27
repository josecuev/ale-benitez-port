# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a portfolio + booking system with two independently deployable services:

- **`ab-frontend/`** — React 19 + Vite 6 SPA (TypeScript, Tailwind CSS v4, Framer Motion, GSAP). Served by Nginx in production.
- **`ab_reservas_project/`** — Django 5.2.8 backend (Python 3.12, Poetry, Uvicorn ASGI). Multiple apps under one Django project.

In production, Traefik routes subdomains to services:
- `alejandrobenitez.com` / `www.` → frontend (Nginx)
- `links.alejandrobenitez.com` → Django `app_links`
- `fractalia.alejandrobenitez.com` → Django `app_fractalia`
- `admin.alejandrobenitez.com` → Django admin

## Django Apps

| App | URL Prefix | Purpose |
|-----|-----------|---------|
| `app_links` | `/` | Linktree-style link aggregator |
| `app_fractalia` | `/fractalia/` | Studio booking calendar + WhatsApp integration |
| `app_portfolio` | `/fotos/` | Portfolio photos API (consumed by React frontend) |
| `app_analytics` | `/api/analytics/` | Privacy-preserving page view tracking |

## Common Commands

All Django commands must be run inside Docker:

```bash
# Start dev environment (Django + PostgreSQL + Nginx)
docker compose -f 2-docker-compose.reservas.yml up

# Start frontend dev server (Vite, port 5173)
docker compose -f 0-docker-compose.dev.yml up

# Django management commands
docker exec ab-reservas-web poetry run python manage.py migrate
docker exec ab-reservas-web poetry run python manage.py createsuperuser
docker exec ab-reservas-web poetry run python manage.py shell

# Seed development data (PendingBookings, Bookings, PageViews)
docker exec ab-reservas-web python seed_dev.py

# Collect static files (done automatically in entrypoint.sh)
docker exec ab-reservas-web poetry run python manage.py collectstatic --noinput
```

Frontend (without Docker):
```bash
cd ab-frontend
pnpm install
pnpm dev        # Dev server on :5173
pnpm build      # TypeScript check + Vite build
pnpm lint       # ESLint
```

Production deploy:
```bash
# Backend
docker compose -f 3-docker-compose.reservas.prod.yml up -d

# Frontend + Traefik
docker compose -f 1-docker-compose.prod.yml up -d
```

## Environment Variables

Copy `.env.example` to `.env` (dev) or `.env.prod` (prod). Key vars:

| Variable | Purpose |
|----------|---------|
| `DATABASE=postgresql` | Enables PostgreSQL (omit for SQLite) |
| `POSTGRES_HOST/PORT/USER/PASSWORD/DB` | PostgreSQL connection |
| `DEBUG` | `1` for dev, `0` for prod |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `SECRET_KEY` | Django secret key |
| `SESSION_COOKIE_DOMAIN` | Set to `.alejandrobenitez.com` in prod |

## Key Implementation Details

**Booking System (`app_fractalia`):**
- `Booking` model enforces no-overlap via `clean()` on save — always validated at DB level.
- `PendingBooking` uses a 4-char alphanumeric code (e.g., `A7K2`) for client lookup.
- Phone validation: Paraguayan format `09XXXXXXXX`, validated both in JS (frontend) and Python (view).
- Availability API cross-checks ALL resources for the same time slot (studio has one physical space).
- Timezone: All datetime logic uses `America/Asuncion` explicitly — never use `timezone.now()` naively.

**Analytics (`app_analytics`):**
- IPs and user-agents are stored as SHA-256 hashes (irreversible by design).
- Referrers stored as domain only — strip full paths before saving.
- Rate limit: 10 requests/minute per IP via Django cache.

**Static/Media Files:**
- Static files: WhiteNoise serves from `staticfiles/` (collected on container start).
- Media files: Nginx serves from `/app/media/`; thumbnails auto-generated on `Photo.save()` (900×900 JPEG).
- Use `./migrate_photos.sh` to bulk-import portfolio photos.

**Frontend ↔ Backend:**
- The React SPA calls `/fotos/` API for portfolio photos (CORS: `*`).
- The analytics tracking calls `/api/analytics/track/` with CORS origin check.
- `app_fractalia` booking form is a standalone Django template (not React).

**Templates:**
- All Django templates use inline styles (no external CSS files).
- Brand: `#ffe927` yellow, Bebas Neue headings, mobile-first with `-webkit-overflow-scrolling: touch`.
