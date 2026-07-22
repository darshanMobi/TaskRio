# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is **not** a runnable application — it's an extracted `admin/` directory (Jinja2 templates + one static JS vendor file) from a larger FastAPI backend for **TaskRio** (internally also referenced as "WAHA Assistant"), a multi-tenant WhatsApp bot SaaS. The actual Python routes, models, and business logic that render these templates live outside this folder and are not present here.

There is no build system, package manifest, linter config, or test suite in this repo — it is purely template/markup source. There are no commands to build, lint, or test.

## Structure

```
admin/
  static/chart.min.js         # vendored Chart.js build, loaded by dashboard.html
  templates/                  # operator-facing admin panel (mounted at /admin/*)
    admin_login.html
    dashboard.html, analytics.html, groups.html, group_detail.html,
    dms.html, dm_detail.html, tenants.html, tenant_detail.html,
    reminders.html, suggestions.html
    tenant_portal/            # per-tenant self-service portal (mounted at /tenant/*)
      base.html, _nav.html    # shared layout + nav, extended via {% extends %}
      login.html, dashboard.html, whatsapp.html,
      groups.html, group_members.html, dms.html, dm_detail.html
```

## Two distinct UIs, two different template conventions

- **`templates/*.html` (top-level admin panel, `/admin/*`)** — each page is a fully standalone HTML document with its own inline `<style>` block (nav, cards, stat grids, badges, buttons are re-declared per file rather than shared). Do not assume changes to one page's CSS affect another — they don't.
- **`templates/tenant_portal/*.html` (`/tenant/*`)** — pages instead use Jinja inheritance: they `{% extends "tenant_portal/base.html" %}` and fill `{% block title %}`, `{% block content %}`, and optionally `{% block extra_style %}` / `{% block extra_script %}`. `base.html` holds the shared `<style>` and includes `tenant_portal/_nav.html` for the top nav. When editing shared chrome (nav links, badge/button styles, card layout) for the tenant portal, edit `base.html`/`_nav.html` once rather than per-page.

When adding a new tenant-portal page, follow the `{% extends %}` pattern (see `whatsapp.html` or `groups.html` as examples), not the standalone-document pattern used in the top-level admin templates.

## Rendering context (inferred from template usage — verify against the actual backend before relying on it)

- Templates are rendered by a FastAPI app using Jinja2 (`request.url.path` is used directly in templates, e.g. in `_nav.html` for active-link highlighting — this is a FastAPI/Starlette `Request` idiom, not Flask).
- `/admin/*` routes require a password login (`admin_login.html` posts to `/admin/login`; password comes from the `ANALYTICS_PASSWORD` env var per the login page's own copy).
- `/tenant/*` routes represent a per-tenant portal with role-based nav (`_nav.html` shows a `role` pill) and its own login (`tenant_portal/login.html`).
- Tenant status is a small state machine surfaced via badges: `active`, `provisioning`, `pending`, `disconnected`, `suspended` (see `.badge-*` classes in `tenant_portal/base.html` and the `statusBadge()` JS helper in `whatsapp.html`).
- Dashboard-style pages (`dashboard.html`, `tenant_portal/dashboard.html`) expect the server to inject a `stats` object and a `chart_data` object (consumed via `{{ chart_data | tojson }}`) and render charts client-side with the vendored Chart.js (`/admin/static/chart.min.js`).
- Pages with live state (e.g. `whatsapp.html`'s QR pairing flow) call a JSON API under the same prefix (e.g. `/tenant/api/status`) via `fetch` and re-render DOM fragments in place — there is no frontend framework/bundler involved, just inline `<script>` blocks per page.

## Working in this repo

Since there's no backend here, changes are markup/CSS/vanilla-JS only. To verify a change actually renders correctly (Jinja logic, JS behavior against real data), you need the companion FastAPI app that owns these routes — check with the user for its location rather than assuming, since it isn't part of this checkout.
