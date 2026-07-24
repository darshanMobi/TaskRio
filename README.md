# TaskRio Admin Templates

This repository contains the **admin-facing frontend** — Jinja2 templates, stylesheets, and static assets — extracted from the TaskRio (internally also referenced as "WAHA Assistant") backend, a multi-tenant WhatsApp bot SaaS platform.

> **Note:** This is not a runnable application on its own. The FastAPI routes, database models, and business logic that render these templates live in a separate backend project and are not included in this checkout. There is no build system, package manifest, linter, or test suite here — this repo is purely markup/CSS/vanilla-JS source.

## Structure

```
admin/
├── static/                       # Stylesheets, vendored JS, and brand assets
│   ├── admin.css                 # Shared styles for the top-level admin panel
│   ├── analytics.css
│   ├── dm_detail.css
│   ├── group_detail.css
│   ├── groups.css
│   ├── reminders.css
│   ├── tenant_detail.css
│   ├── tenants.css
│   ├── dark-theme.css            # Dark mode overrides
│   ├── theme-toggle.css          # Light/dark theme toggle control
│   ├── chart.min.js              # Vendored Chart.js build (used by dashboard.html)
│   ├── logo.svg / logo.png / logo-dark.png
│   └── favicon.ico / favicon.svg / favicon-16.png / favicon-32.png / favicon-192.png / favicon-512.png / apple-touch-icon.png
│
└── templates/
    ├── index.html                # Entry/landing template
    ├── admin_login.html          # Password-gated login for /admin/*
    ├── dashboard.html            # Stats + Chart.js charts (expects `stats`, `chart_data`)
    ├── analytics.html
    ├── groups.html / group_detail.html
    ├── dms.html / dm_detail.html
    ├── tenants.html / tenant_detail.html
    ├── reminders.html
    ├── suggestions.html
    │
    └── tenant_portal/            # Per-tenant self-service portal (/tenant/*)
        ├── base.html             # Shared layout + <style>, extended by all other pages
        ├── _nav.html             # Shared top nav, included by base.html
        ├── login.html
        ├── dashboard.html
        ├── whatsapp.html         # QR pairing flow, polls /tenant/api/status
        ├── groups.html / group_members.html
        └── dms.html / dm_detail.html
```

## Two distinct UI conventions

This repo mixes two different templating approaches depending on which surface a page belongs to:

- **Top-level admin panel (`admin/templates/*.html`, mounted at `/admin/*`)** — each page is a standalone HTML document. Layout and component styles (nav, cards, stat grids, badges, buttons) are largely re-declared per page rather than shared, though common rules now also live in `admin/static/admin.css` and the page-specific `*.css` files. Don't assume a change to one page's styling automatically applies to another.
- **Tenant portal (`admin/templates/tenant_portal/*.html`, mounted at `/tenant/*`)** — pages use Jinja template inheritance. Each page does `{% extends "tenant_portal/base.html" %}` and fills in `{% block title %}`, `{% block content %}`, and optionally `{% block extra_style %}` / `{% block extra_script %}`. Shared chrome (nav links, badges, buttons, card layout) lives once in `base.html` and `_nav.html` — edit those files rather than duplicating styles per page.

When adding a new tenant-portal page, follow the `{% extends %}` pattern used by `whatsapp.html` or `groups.html`. Do not use the standalone-document pattern from the top-level admin templates.

## Rendering context

These templates are designed to be rendered by a FastAPI app using Jinja2. Some notable conventions inferred from template usage (verify against the actual backend before relying on them):

- `request.url.path` is referenced directly in templates (e.g. in `_nav.html` for active-link highlighting) — a FastAPI/Starlette `Request` idiom, not Flask.
- `/admin/*` routes require a password login. `admin_login.html` posts to `/admin/login`; the password is sourced from the `ANALYTICS_PASSWORD` environment variable per the login page's own copy.
- `/tenant/*` routes serve a per-tenant portal with role-based navigation (`_nav.html` renders a `role` pill) and its own login flow (`tenant_portal/login.html`).
- Tenant status is a small state machine surfaced via badges: `active`, `provisioning`, `pending`, `disconnected`, `suspended` — see the `.badge-*` classes in `tenant_portal/base.html` and the `statusBadge()` JS helper in `whatsapp.html`.
- Dashboard-style pages (`dashboard.html`, `tenant_portal/dashboard.html`) expect the server to inject a `stats` object and a `chart_data` object (consumed via `{{ chart_data | tojson }}`), rendered client-side with the vendored Chart.js at `admin/static/chart.min.js`.
- Pages with live state — e.g. `whatsapp.html`'s QR pairing flow — call a JSON API under the same prefix (e.g. `/tenant/api/status`) via `fetch` and re-render DOM fragments in place. There is no frontend framework or bundler; each page uses inline `<script>` blocks.
- Both the top-level admin panel and the tenant portal support a light/dark theme toggle (`dark-theme.css`, `theme-toggle.css`).

## Working in this repo

Since the backend isn't included here, changes are limited to markup, CSS, and vanilla JS. To verify that a change actually renders correctly — Jinja logic, live data, JS behavior — you need the companion FastAPI application that owns these routes and supplies `stats`, `chart_data`, tenant/group/DM records, etc. Check with whoever owns that backend for its location before assuming template changes work end-to-end.
