"""
Throwaway STUB FastAPI app for previewing the admin_templates/ Jinja templates
in a browser.

This is NOT the real TaskRio backend - there is no real auth, no real database,
no real WhatsApp/WAHA integration. All data lives in mock_data.py as in-memory
Python structures that get mutated by this process and reset on restart.

Run with:
    pip install -r requirements.txt
    uvicorn app:app --reload
Then open http://127.0.0.1:8000/admin and http://127.0.0.1:8000/tenant
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import mock_data as md

app = FastAPI(title="TaskRio admin/tenant preview (stub)")

templates = Jinja2Templates(directory="admin/templates")
app.mount("/admin/static", StaticFiles(directory="admin/static"), name="admin_static")

# The tenant portal preview always "logs in" as this one tenant.
CURRENT_TENANT_ID = next(t["id"] for t in md.TENANTS.values() if t["name"] == "Acme Corp")


def render(request: Request, name: str, **context):
    return templates.TemplateResponse(request, name, context)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/")
def index(request: Request):
    return render(request, "index.html")


# ---------------------------------------------------------------------------
# Admin auth (mocked - any password works, cookie is just a marker)
# ---------------------------------------------------------------------------

@app.get("/admin/login")
def admin_login_page(request: Request):
    return render(request, "admin_login.html", error=None)


@app.post("/admin/login")
def admin_login_submit(request: Request):
    resp = RedirectResponse(url="/admin", status_code=303)
    resp.set_cookie("admin_session", "1")
    return resp


@app.get("/admin/logout")
def admin_logout():
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie("admin_session")
    return resp


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

@app.get("/admin")
def admin_dashboard(request: Request):
    return render(
        request,
        "dashboard.html",
        stats=md.build_dashboard_stats(),
        chart_data=md.build_dashboard_chart_data(),
    )


# ---------------------------------------------------------------------------
# Admin: groups
# ---------------------------------------------------------------------------

@app.get("/admin/groups")
def admin_groups_page(request: Request):
    return render(request, "groups.html")


@app.get("/admin/group/{group_id}")
def admin_group_detail_page(request: Request, group_id: str):
    return render(request, "group_detail.html")


@app.get("/admin/pending-group-invites")
def admin_pending_group_invites():
    return {"invites": md.PENDING_GROUP_INVITES}


@app.post("/admin/pending-group-invites/{invite_id}/approve")
def admin_approve_pending_invite(invite_id: int):
    inv = next((i for i in md.PENDING_GROUP_INVITES if i["id"] == invite_id), None)
    if not inv:
        return JSONResponse({"detail": "Invite not found"}, status_code=404)
    md.PENDING_GROUP_INVITES.remove(inv)
    gid = f"12036340{md.next_id()}@g.us"
    md.GROUPS[gid] = {
        "group_id": gid,
        "group_name": inv["group_name"],
        "status": "approved",
        "is_active": True,
        "message_volume": md.rand_sparkline(),
        "added_at": md.iso(md.NOW),
        "last_seen": md.iso(md.NOW),
        "added_by": "admin",
        "notes": "Joined via approved invite",
        "tenant_name": inv.get("tenant_name"),
        "message_count": 0,
        "last_activity": md.iso(md.NOW),
        "invited_by": inv["invited_by_phone"],
        "messages": [],
        "members": [],
    }
    return {"ok": True}


@app.post("/admin/pending-group-invites/{invite_id}/reject")
def admin_reject_pending_invite(invite_id: int):
    inv = next((i for i in md.PENDING_GROUP_INVITES if i["id"] == invite_id), None)
    if inv:
        md.PENDING_GROUP_INVITES.remove(inv)
    return {"ok": True}


@app.get("/admin/approved-groups")
def admin_list_groups(active: str | None = None):
    return {"groups": list(md.GROUPS.values())}


@app.post("/admin/approved-groups")
async def admin_approve_group(request: Request):
    body = await request.json()
    gid = body.get("group_id")
    existing = md.GROUPS.get(gid, {})
    md.GROUPS[gid] = {
        **existing,
        "group_id": gid,
        "group_name": body.get("group_name") or existing.get("group_name") or gid,
        "status": "approved",
        "is_active": True,
        "message_volume": existing.get("message_volume") or md.rand_sparkline(),
        "added_at": md.iso(md.NOW),
        "last_seen": existing.get("last_seen") or md.iso(md.NOW),
        "added_by": body.get("added_by") or "admin",
        "notes": body.get("notes") or "",
        "tenant_name": body.get("tenant_name") or existing.get("tenant_name"),
        "message_count": existing.get("message_count", 0),
        "last_activity": existing.get("last_activity") or md.iso(md.NOW),
        "invited_by": existing.get("invited_by"),
        "messages": existing.get("messages", []),
        "members": existing.get("members", []),
    }
    return {"ok": True, "group": md.GROUPS[gid]}


@app.post("/admin/rejected-groups")
async def admin_reject_group(request: Request):
    body = await request.json()
    gid = body.get("group_id")
    existing = md.GROUPS.get(gid, {})
    md.GROUPS[gid] = {
        **existing,
        "group_id": gid,
        "group_name": body.get("group_name") or existing.get("group_name") or gid,
        "status": "rejected",
        "is_active": False,
        "message_volume": existing.get("message_volume") or [],
        "added_at": existing.get("added_at"),
        "last_seen": existing.get("last_seen"),
        "added_by": body.get("added_by") or "admin",
        "notes": body.get("notes") or "",
        "tenant_name": existing.get("tenant_name"),
        "message_count": existing.get("message_count", 0),
        "last_activity": existing.get("last_activity"),
        "invited_by": existing.get("invited_by"),
        "messages": existing.get("messages", []),
        "members": existing.get("members", []),
    }
    return {"ok": True}


@app.delete("/admin/rejected-groups/{group_id}")
def admin_unreject_group(group_id: str):
    g = md.GROUPS.get(group_id)
    if g:
        g["status"] = "unapproved"
    return {"ok": True}


@app.post("/admin/approved-groups/{group_id}/activate")
def admin_activate_group(group_id: str):
    g = md.GROUPS.get(group_id)
    if not g:
        return JSONResponse({"detail": "Group not found"}, status_code=404)
    g["is_active"] = True
    return {"ok": True}


@app.delete("/admin/approved-groups/{group_id}")
def admin_deactivate_group(group_id: str):
    g = md.GROUPS.get(group_id)
    if not g:
        return JSONResponse({"detail": "Group not found"}, status_code=404)
    g["is_active"] = False
    return {"ok": True}


@app.get("/admin/group-detail/{group_id}")
def admin_group_detail(group_id: str):
    g = md.GROUPS.get(group_id)
    if not g:
        return JSONResponse({"detail": "Group not found"}, status_code=404)
    return g


@app.get("/admin/groups/{group_id}/members")
def admin_group_members(group_id: str):
    return {"members": md.get_group_members(group_id)}


@app.post("/admin/groups/{group_id}/members/{wa_id}/block")
def admin_block_group_member(group_id: str, wa_id: str):
    for m in md.get_group_members(group_id):
        if m["wa_id"] == wa_id:
            m["blocked"] = True
    return {"ok": True}


@app.post("/admin/groups/{group_id}/members/{wa_id}/unblock")
def admin_unblock_group_member(group_id: str, wa_id: str):
    for m in md.get_group_members(group_id):
        if m["wa_id"] == wa_id:
            m["blocked"] = False
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin: tenants
# ---------------------------------------------------------------------------

@app.get("/admin/tenants")
def admin_tenants_page(request: Request):
    return render(request, "tenants.html")


@app.get("/admin/tenants-list")
def admin_tenants_list():
    return {"tenants": list(md.TENANTS.values())}


@app.post("/admin/tenants")
async def admin_create_tenant(request: Request):
    body = await request.json()
    t = md._make_tenant(
        body.get("name") or "New Tenant",
        "pending",
        body.get("plan") or "standard",
        is_internal=bool(body.get("is_internal")),
        msisdn=body.get("wa_msisdn"),
    )
    if body.get("owner_phone"):
        t["members"] = [{"phone": body["owner_phone"], "role": "owner"}]
    md.TENANTS[t["id"]] = t
    return {"ok": True, "tenant": t}


@app.post("/admin/tenants/sync-webhooks")
def admin_sync_webhooks():
    synced = [t["wa_session_name"] for t in md.TENANTS.values() if t["status"] != "pending"]
    return {"synced": synced, "failed": []}


@app.get("/admin/tenant/{tenant_id}")
def admin_tenant_detail_page(request: Request, tenant_id: str):
    return render(request, "tenant_detail.html", tenant_id=tenant_id)


@app.get("/admin/tenants/{tenant_id}")
def admin_get_tenant(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    return {"tenant": t}


@app.post("/admin/tenants/{tenant_id}/provision")
def admin_provision_tenant(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    t["status"] = "provisioning"
    return {"ok": True, "tenant": t}


@app.post("/admin/tenants/{tenant_id}/retry")
def admin_retry_tenant(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    t["status"] = "provisioning"
    t["link_error"] = ""
    return {"ok": True, "tenant": t}


@app.post("/admin/tenants/{tenant_id}/cancel")
def admin_cancel_tenant_provisioning(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    t["status"] = "pending"
    return {"ok": True, "tenant": t}


@app.post("/admin/tenants/{tenant_id}/activate")
def admin_activate_tenant(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    t["status"] = "active"
    t["link_error"] = ""
    if not t.get("activated_at"):
        t["activated_at"] = md.iso(md.NOW)
    return {"ok": True, "tenant": t}


@app.post("/admin/tenants/{tenant_id}/deactivate")
def admin_deactivate_tenant(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    t["status"] = "suspended"
    return {"ok": True, "tenant": t}


@app.get("/admin/tenants/{tenant_id}/qr")
def admin_tenant_qr(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    # 30% chance to simulate "not ready yet" like a real WAHA session mid-pairing.
    return {"mimetype": "image/png", "data": md.FAKE_QR_PNG_B64}


@app.get("/admin/tenants/{tenant_id}/status")
def admin_tenant_live_status(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    # Simulate provisioning finishing after being polled.
    if t["status"] == "provisioning":
        t["status"] = "active"
        t["activated_at"] = md.iso(md.NOW)
        t["wa_msisdn"] = t["wa_msisdn"] or "+1 555 200 5555"
    return {"ok": True, "tenant": t}


@app.delete("/admin/tenants/{tenant_id}")
def admin_delete_tenant(tenant_id: str):
    md.TENANTS.pop(tenant_id, None)
    return {"ok": True}


@app.get("/admin/tenants/{tenant_id}/webhook-config")
def admin_get_webhook_config(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    return t["webhook"]


@app.put("/admin/tenants/{tenant_id}/webhook-config")
async def admin_save_webhook_config(tenant_id: str, request: Request):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    body = await request.json()
    t["webhook"]["events"] = body.get("events", [])
    return {"ok": True}


@app.get("/admin/tenants/{tenant_id}/groups")
def admin_tenant_groups(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    return {"groups": t.get("groups", [])}


@app.post("/admin/tenants/{tenant_id}/groups/{group_id}/approve")
def admin_tenant_group_approve(tenant_id: str, group_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    for g in t.get("groups", []):
        if g["id"] == group_id:
            g["status"] = "approved"
    return {"ok": True}


@app.post("/admin/tenants/{tenant_id}/groups/{group_id}/reject")
def admin_tenant_group_reject(tenant_id: str, group_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    for g in t.get("groups", []):
        if g["id"] == group_id:
            g["status"] = "rejected"
    return {"ok": True}


@app.get("/admin/tenants/{tenant_id}/members")
def admin_tenant_members(tenant_id: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    return {"members": t.get("members", [])}


@app.post("/admin/tenants/{tenant_id}/members")
async def admin_tenant_add_member(tenant_id: str, request: Request):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    body = await request.json()
    t.setdefault("members", []).append({"phone": body["phone"], "role": body.get("role", "member")})
    return {"ok": True}


@app.delete("/admin/tenants/{tenant_id}/members/{phone}")
def admin_tenant_remove_member(tenant_id: str, phone: str):
    t = md.TENANTS.get(tenant_id)
    if not t:
        return JSONResponse({"detail": "Tenant not found"}, status_code=404)
    t["members"] = [m for m in t.get("members", []) if m["phone"] != phone]
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin: DMs
# ---------------------------------------------------------------------------

@app.get("/admin/dms")
def admin_dms_page(request: Request):
    return render(request, "dms.html")


@app.get("/admin/dm-list")
def admin_dm_list(active: str | None = None):
    return {"dms": list(md.DMS.values())}


@app.get("/admin/dm/{wa_id}")
def admin_dm_detail_page(request: Request, wa_id: str):
    return render(request, "dm_detail.html", wa_id=wa_id)


@app.get("/admin/dm-detail/{wa_id}")
def admin_dm_detail(wa_id: str):
    dm = md.DMS.get(wa_id)
    if not dm:
        # Any wa_id not yet known (e.g. linked from analytics) gets a thin fake record
        dm = md._make_dm("Unknown User", "+" + wa_id.split("@")[0])
        md.DMS[wa_id] = dm
    return dm


@app.post("/admin/dm-send-message")
async def admin_dm_send_message(request: Request):
    body = await request.json()
    wa_id = body.get("wa_id")
    dm = md.DMS.get(wa_id)
    if dm:
        dm["messages"].append({
            "kind": "outbound",
            "sender": "TaskRio",
            "timestamp": md.iso(md.NOW),
            "text": body.get("message", ""),
        })
        dm["message_count"] += 1
        dm["last_activity"] = md.iso(md.NOW)
    return {"success": True}


# ---------------------------------------------------------------------------
# Admin: analytics / demo funnel
# ---------------------------------------------------------------------------

@app.get("/admin/analytics")
def admin_analytics_page(request: Request):
    return render(request, "analytics.html")


@app.get("/analytics/tutorial-funnel")
def analytics_tutorial_funnel(days: int = 7):
    return md.build_tutorial_funnel(days)


@app.get("/analytics/daily-activity")
def analytics_daily_activity(days: int = 7):
    return md.build_daily_activity(days)


@app.get("/analytics/user-details")
def analytics_user_details(user_ids: str = ""):
    ids = [u for u in user_ids.split(",") if u]
    return {"users": md.get_user_details(ids)}


# ---------------------------------------------------------------------------
# Admin: suggestions
# ---------------------------------------------------------------------------

@app.get("/admin/suggestions")
def admin_suggestions_page(request: Request):
    return render(request, "suggestions.html", suggestions=md.SUGGESTIONS)


# ---------------------------------------------------------------------------
# Admin: reminders
# ---------------------------------------------------------------------------

@app.get("/admin/reminders")
def admin_reminders_page(request: Request, period: str = "7d"):
    ctx = md.build_reminders_context(period)
    return render(request, "reminders.html", **ctx)


# ---------------------------------------------------------------------------
# Tenant portal auth (mocked - any phone/OTP works)
# ---------------------------------------------------------------------------

@app.get("/tenant/login")
def tenant_login_page(request: Request):
    return render(request, "tenant_portal/login.html")


@app.post("/tenant/login/request-otp")
async def tenant_request_otp(request: Request):
    return {"ok": True}


@app.post("/tenant/login/verify-otp")
async def tenant_verify_otp(request: Request):
    resp = JSONResponse({"redirect": "/tenant"})
    resp.set_cookie("tenant_session", "1")
    return resp


@app.get("/tenant/logout")
def tenant_logout():
    resp = RedirectResponse(url="/tenant/login", status_code=303)
    resp.delete_cookie("tenant_session")
    return resp


# ---------------------------------------------------------------------------
# Tenant portal pages
# ---------------------------------------------------------------------------

ROLE = "owner"


@app.get("/tenant")
def tenant_dashboard(request: Request):
    t = md.TENANTS[CURRENT_TENANT_ID]
    pending_count = len(md.PENDING_GROUP_INVITES)
    return render(request, "tenant_portal/dashboard.html", tenant=t, pending_count=pending_count, role=ROLE)


@app.get("/tenant/whatsapp")
def tenant_whatsapp_page(request: Request):
    return render(request, "tenant_portal/whatsapp.html", role=ROLE)


@app.get("/tenant/groups")
def tenant_groups_page(request: Request):
    return render(request, "tenant_portal/groups.html", role=ROLE)


@app.get("/tenant/groups/{group_id}/members")
def tenant_group_members_page(request: Request, group_id: str):
    return render(request, "tenant_portal/group_members.html", group_id=group_id, role=ROLE)


@app.get("/tenant/dms")
def tenant_dms_page(request: Request):
    return render(request, "tenant_portal/dms.html", role=ROLE)


@app.get("/tenant/dm/{dm_id}")
def tenant_dm_detail_page(request: Request, dm_id: str):
    return render(request, "tenant_portal/dm_detail.html", wa_id=dm_id, role=ROLE)


# ---------------------------------------------------------------------------
# Tenant portal JSON API
# ---------------------------------------------------------------------------

@app.get("/tenant/api/status")
def tenant_api_status():
    return {"tenant": md.TENANTS[CURRENT_TENANT_ID]}


@app.post("/tenant/api/provision")
def tenant_api_provision():
    t = md.TENANTS[CURRENT_TENANT_ID]
    t["status"] = "provisioning"
    return {"ok": True, "tenant": t}


@app.post("/tenant/api/retry")
def tenant_api_retry():
    t = md.TENANTS[CURRENT_TENANT_ID]
    t["status"] = "provisioning"
    t["link_error"] = ""
    return {"ok": True, "tenant": t}


@app.post("/tenant/api/cancel")
def tenant_api_cancel():
    t = md.TENANTS[CURRENT_TENANT_ID]
    t["status"] = "pending"
    return {"ok": True, "tenant": t}


@app.post("/tenant/api/unlink")
def tenant_api_unlink():
    t = md.TENANTS[CURRENT_TENANT_ID]
    t["status"] = "disconnected"
    t["link_error"] = "Device unlinked by user."
    return {"ok": True, "tenant": t}


@app.get("/tenant/api/qr")
def tenant_api_qr():
    return {"mimetype": "image/png", "data": md.FAKE_QR_PNG_B64}


@app.get("/tenant/api/pending-invites")
def tenant_api_pending_invites():
    return {"invites": md.PENDING_GROUP_INVITES}


@app.post("/tenant/api/pending-invites/{invite_id}/approve")
def tenant_api_approve_invite(invite_id: int):
    return admin_approve_pending_invite(invite_id)


@app.post("/tenant/api/pending-invites/{invite_id}/reject")
def tenant_api_reject_invite(invite_id: int):
    return admin_reject_pending_invite(invite_id)


@app.get("/tenant/api/groups")
def tenant_api_groups():
    t = md.TENANTS[CURRENT_TENANT_ID]
    return {"groups": t.get("groups", [])}


@app.post("/tenant/api/groups/{group_id}/approve")
def tenant_api_group_approve(group_id: str):
    return admin_tenant_group_approve(CURRENT_TENANT_ID, group_id)


@app.post("/tenant/api/groups/{group_id}/reject")
def tenant_api_group_reject(group_id: str):
    return admin_tenant_group_reject(CURRENT_TENANT_ID, group_id)


@app.get("/tenant/api/groups/{group_id}/members")
def tenant_api_group_members(group_id: str):
    return admin_group_members(group_id)


@app.post("/tenant/api/groups/{group_id}/members/{wa_id}/block")
def tenant_api_block_member(group_id: str, wa_id: str):
    return admin_block_group_member(group_id, wa_id)


@app.post("/tenant/api/groups/{group_id}/members/{wa_id}/unblock")
def tenant_api_unblock_member(group_id: str, wa_id: str):
    return admin_unblock_group_member(group_id, wa_id)


@app.get("/tenant/api/dms")
def tenant_api_dms():
    return {"dms": list(md.DMS.values())}


@app.get("/tenant/api/dms/{wa_id}")
def tenant_api_dm_detail(wa_id: str):
    return admin_dm_detail(wa_id)


@app.post("/tenant/api/dms/send")
async def tenant_api_dm_send(request: Request):
    return await admin_dm_send_message(request)
