"""
In-memory fake data for the admin_templates preview server.

This is throwaway data for a preview/stub app only - nothing here is persisted,
validated, or business-logic-correct. It exists purely to give the Jinja
templates and their fetch() calls something plausible to render.
"""
from __future__ import annotations

import itertools
import random
import uuid
from datetime import datetime, timedelta, timezone

random.seed(42)

NOW = datetime.now(timezone.utc)

# A 1x1 transparent PNG, used as a stand-in "QR code" image everywhere a QR is requested.
FAKE_QR_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUAAarVyFEA"
    "AAAASUVORK5CYII="
)

_id_counter = itertools.count(1)


def next_id() -> int:
    return next(_id_counter)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def rand_sparkline(n: int = 30, lo: int = 0, hi: int = 40) -> list[int]:
    return [random.randint(lo, hi) for _ in range(n)]


def days_ago(d: float) -> datetime:
    return NOW - timedelta(days=d)


def hours_ago(h: float) -> datetime:
    return NOW - timedelta(hours=h)


# ---------------------------------------------------------------------------
# Approved / unapproved / rejected groups (admin panel)
# ---------------------------------------------------------------------------

GROUPS: dict[str, dict] = {}


def _seed_groups():
    samples = [
        ("120363406296739501@g.us", "Marketing Team", "approved", True, "admin", "Core team group", "Acme Corp"),
        ("120363406296739502@g.us", "Product Standup", "approved", True, "admin", "", "Acme Corp"),
        ("120363406296739503@g.us", "Support Escalations", "approved", False, "admin", "Paused - low activity", "Globex LLC"),
        ("120363406296739504@g.us", "Random Family Group", "unapproved", False, None, None, None),
        ("120363406296739505@g.us", "Spam Test Group", "rejected", False, "admin", "Looked like spam", None),
    ]
    for gid, name, status, active, added_by, notes, tenant_name in samples:
        GROUPS[gid] = {
            "group_id": gid,
            "group_name": name,
            "status": status,
            "is_active": active,
            "message_volume": rand_sparkline(),
            "added_at": iso(days_ago(random.uniform(5, 60))) if status != "unapproved" else None,
            "last_seen": iso(hours_ago(random.uniform(1, 72))),
            "added_by": added_by,
            "notes": notes,
            "tenant_name": tenant_name,
            "message_count": random.randint(50, 5000),
            "last_activity": iso(hours_ago(random.uniform(1, 72))),
            "invited_by": "+1 555 010 0100" if status == "unapproved" else None,
            "messages": [
                {
                    "sender": random.choice(["Alice", "Bob", "Carlos", "Deepa"]),
                    "timestamp": iso(hours_ago(i * 1.3)),
                    "text": random.choice([
                        "Can someone create a task for the client follow-up?",
                        "@TaskRio remind me tomorrow at 9am",
                        "Done with the deck, sharing now.",
                        "What's the status on the invoice?",
                        "Thanks, marking this as complete.",
                    ]),
                }
                for i in range(15)
            ],
            "members": [
                {"wa_id": f"9199250{n:05d}@c.us", "name": name2, "blocked": blocked}
                for n, (name2, blocked) in enumerate([
                    ("Alice Sharma", False),
                    ("Bob Iyer", False),
                    ("Carlos Mehta", True),
                    ("Deepa Rao", False),
                ])
            ],
        }


_seed_groups()

GROUP_MEMBERS: dict[str, list[dict]] = {gid: g["members"] for gid, g in GROUPS.items()}


def get_group_members(group_id: str) -> list[dict]:
    """Return this group's participant list, lazily fabricating one for group
    ids that live outside the main GROUPS dict (e.g. a tenant's own WhatsApp
    groups, which are tracked separately from the admin approved-groups list).
    """
    if group_id not in GROUP_MEMBERS:
        names = ["Alice Sharma", "Bob Iyer", "Carlos Mehta", "Deepa Rao"]
        GROUP_MEMBERS[group_id] = [
            {"wa_id": f"9199252{n:04d}@c.us", "name": name, "blocked": False}
            for n, name in enumerate(names)
        ]
    return GROUP_MEMBERS[group_id]


PENDING_GROUP_INVITES: list[dict] = [
    {
        "id": next_id(),
        "group_name": "New Client - Acme Corp",
        "invited_by_phone": "+1 555 010 0200",
        "tenant_name": "Acme Corp",
        "tenant_id": None,
        "created_at": iso(hours_ago(5)),
    },
    {
        "id": next_id(),
        "group_name": "Ops Sync",
        "invited_by_phone": "+1 555 010 0300",
        "tenant_name": None,
        "tenant_id": None,
        "created_at": iso(hours_ago(20)),
    },
]


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

TENANTS: dict[str, dict] = {}


def _make_tenant(name, status, plan, is_internal=False, msisdn=None) -> dict:
    tid = str(uuid.uuid4())
    session_name = "wa-" + name.lower().replace(" ", "-")
    created = days_ago(random.uniform(2, 120))
    activated = created + timedelta(days=1) if status == "active" else None
    return {
        "id": tid,
        "name": name,
        "wa_session_name": session_name,
        "wa_msisdn": msisdn,
        "status": status,
        "plan": plan,
        "is_internal": is_internal,
        "created_at": iso(created),
        "activated_at": iso(activated),
        "link_error": "" if status != "disconnected" else "Session lost connection to WhatsApp.",
        "members": [
            {"phone": "+1 555 010 0000", "role": "owner"},
        ],
        "groups": [
            {"id": f"1203634{random.randint(10000,99999)}@g.us", "name": f"{name} Team", "size": random.randint(3, 40), "status": random.choice(["approved", "pending", "rejected"])}
            for _ in range(random.randint(0, 3))
        ] if status == "active" else [],
        "webhook": {
            "url": f"https://waha.example.com/webhooks/{session_name}" if status != "pending" else None,
            "events": ["message", "message.ack", "session.status"] if status != "pending" else [],
        },
    }


def _seed_tenants():
    for t in [
        _make_tenant("Acme Corp", "active", "pro", msisdn="+1 555 200 1000"),
        _make_tenant("Globex LLC", "provisioning", "standard"),
        _make_tenant("Initech", "pending", "standard"),
        _make_tenant("Umbrella Inc", "disconnected", "pro", msisdn="+1 555 200 2000"),
        _make_tenant("Internal Demo", "active", "private", is_internal=True, msisdn="+1 555 200 9999"),
        _make_tenant("Soylent Co", "suspended", "standard", msisdn="+1 555 200 3000"),
    ]:
        TENANTS[t["id"]] = t


_seed_tenants()


# ---------------------------------------------------------------------------
# DMs
# ---------------------------------------------------------------------------

DMS: dict[str, dict] = {}


def _make_dm(name, phone, tz=None, auto=False) -> dict:
    wa_id = f"{phone.lstrip('+')}@c.us"
    msg_count = random.randint(5, 800)
    messages = []
    for i in range(min(msg_count, 40)):
        inbound = i % 2 == 0
        messages.append({
            "kind": "inbound" if inbound else "outbound",
            "sender": name if inbound else "TaskRio",
            "timestamp": iso(hours_ago((40 - i) * 3)),
            "text": random.choice([
                "Add task: follow up with vendor tomorrow",
                "Sure! I've created that task for you.",
                "What tasks do I have open?",
                "You have 3 open tasks. Want me to list them?",
                "Remind me at 5pm to call the client",
                "Got it, I'll remind you at 5:00 PM.",
            ]),
        })
    return {
        "wa_id": wa_id,
        "display_name": name,
        "phone": phone,
        "timezone": tz,
        "auto_detected": auto,
        "message_count": msg_count,
        "first_seen": iso(days_ago(random.uniform(10, 200))),
        "last_activity": iso(hours_ago(random.uniform(1, 96))),
        "message_volume": rand_sparkline(),
        "messages": list(reversed(messages)),
    }


def _seed_dms():
    samples = [
        ("Alice Sharma", "+919925001111", "Asia/Kolkata", True),
        ("Bob Iyer", "+919925002222", "Asia/Kolkata", False),
        ("Carlos Mehta", "+15550100333", "America/New_York", True),
        ("Deepa Rao", "+919925004444", None, False),
        ("Evan Wright", "+447700900555", "Europe/London", True),
    ]
    for name, phone, tz, auto in samples:
        dm = _make_dm(name, phone, tz, auto)
        DMS[dm["wa_id"]] = dm


_seed_dms()


# ---------------------------------------------------------------------------
# Suggestions (shadow mode)
# ---------------------------------------------------------------------------

SUGGESTIONS: list[dict] = [
    {
        "created_at": iso(hours_ago(i * 4)),
        "group_id": random.choice(list(GROUPS.keys())),
        "kind": random.choice(["task_create", "reminder", "priority_update"]),
        "confidence": round(random.uniform(0.55, 0.98), 2),
        "text": random.choice([
            "Looks like a task: 'follow up with the vendor by Friday'",
            "Detected reminder intent: 'ping me tomorrow morning'",
            "Possible priority bump on task #482",
        ]),
        "sugg_id": str(uuid.uuid4())[:8],
    }
    for i in range(12)
]


# ---------------------------------------------------------------------------
# Reminders analytics
# ---------------------------------------------------------------------------

def build_reminders_context(period: str) -> dict:
    days_map = {"1d": 1, "7d": 7, "30d": 30, "all": 90}
    n_days = days_map.get(period, 7)

    if period == "1d":
        labels = [f"{h:02d}:00" for h in range(24)]
        counts = [random.randint(0, 15) for _ in range(24)]
    else:
        labels = [(NOW - timedelta(days=n_days - 1 - i)).strftime("%b %d") for i in range(n_days)]
        counts = [random.randint(5, 60) for _ in range(n_days)]

    total_reminders = sum(counts)
    unique_users = random.randint(10, total_reminders // 2 + 5)
    new_reminded_users = max(1, unique_users // 4)

    stats = {
        "total_reminders": total_reminders,
        "unique_users": unique_users,
        "new_reminded_users": new_reminded_users,
        "response_rate": round(random.uniform(35, 75), 1),
        "actions_done": random.randint(10, 200),
        "actions_reschedule": random.randint(5, 80),
        "actions_snooze": random.randint(5, 60),
        "reminder_kinds": {"task_due": random.randint(20, 150), "follow_up": random.randint(10, 90), "custom": random.randint(5, 40)},
    }

    def fake_user(i):
        first = days_ago(random.uniform(0.1, n_days))
        last = first + timedelta(hours=random.uniform(1, 48))
        return {
            "user_id": f"9199250{1000+i}@c.us",
            "display_name": random.choice(["Alice Sharma", "Bob Iyer", None, "Deepa Rao", None]),
            "first_reminder_at": first,
            "first_reminder_ever": first - timedelta(days=random.uniform(0, 30)),
            "last_reminder_sent": last,
            "total_reminders_sent": random.randint(1, 25),
            "tasks_with_reminders": random.randint(1, 10),
        }

    new_users_list = [fake_user(i) for i in range(min(new_reminded_users, 15))]
    unique_users_list = [fake_user(i) for i in range(min(unique_users, 50))]

    return {
        "period": period,
        "stats": stats,
        "chart_data": {"labels": labels, "counts": counts},
        "new_users_list": new_users_list,
        "unique_users_list": unique_users_list,
    }


# ---------------------------------------------------------------------------
# Tutorial funnel analytics (/analytics/*)
# ---------------------------------------------------------------------------

_FUNNEL_USERS: list[dict] = []


def _seed_funnel_users(n=40):
    for i in range(n):
        started_at = days_ago(random.uniform(0.5, 60))
        current_step = random.choices([0, 1, 2, 3, 4, 5], weights=[10, 20, 20, 15, 15, 20])[0]
        completed = current_step == 5

        def step_time(step_no):
            if current_step >= step_no:
                return started_at + timedelta(minutes=step_no * random.uniform(2, 20))
            return None

        _FUNNEL_USERS.append({
            "user_id": f"9199251{2000+i}@c.us",
            "original_user_id": f"9199251{2000+i}@c.us",
            "phone_number": f"+9199251{2000+i}",
            "display_name": random.choice(["Alice Sharma", "Bob Iyer", None, "Carlos Mehta", None, "Deepa Rao"]),
            "current_step": current_step,
            "completed": completed,
            "total_attempts": random.choices([1, 2, 3], weights=[70, 20, 10])[0],
            "started_at": started_at,
            "demo_timestamp": started_at,
            "first_task_at": step_time(1),
            "completed_at": step_time(5) if completed else None,
            "tasks_created": random.randint(0, 6),
            "message_count": random.randint(3, 60),
            "last_seen": started_at + timedelta(hours=random.uniform(0, 72)),
        })


_seed_funnel_users()


def build_tutorial_funnel(days: int) -> dict:
    cutoff = days_ago(days)
    users = [u for u in _FUNNEL_USERS if u["started_at"] >= cutoff]

    def bucket(min_step):
        return [{"user_id": u["user_id"]} for u in users if u["current_step"] >= min_step]

    started = bucket(0)
    step1 = bucket(1)
    step2 = bucket(2)
    step3 = bucket(3)
    step4 = bucket(4)
    complete = bucket(5)

    def rate(n, total):
        return round((n / total * 100), 1) if total else 0.0

    total = len(started)
    return {
        "summary": {
            "total_started": total,
            "completed_step1": len(step1),
            "completed_step2": len(step2),
            "completed_step3": len(step3),
            "completed_step4": len(step4),
            "completed_all": len(complete),
        },
        "conversion_rates": {
            "step1_rate": rate(len(step1), total),
            "step2_rate": rate(len(step2), total),
            "step3_rate": rate(len(step3), total),
            "step4_rate": rate(len(step4), total),
            "completion_rate": rate(len(complete), total),
        },
        "users": {
            "started": started,
            "completed_step1": step1,
            "completed_step2": step2,
            "completed_step3": step3,
            "completed_step4": step4,
            "completed_all": complete,
        },
    }


def build_daily_activity(days: int) -> dict:
    def day_series():
        series = []
        for i in range(days):
            d = NOW - timedelta(days=i)
            series.append({"date": d.strftime("%Y-%m-%d"), "count": random.randint(0, 20)})
        return series  # newest first, matching the template's .reverse() expectation

    return {
        "tutorial_starts_by_day": day_series(),
        "tasks_created_by_day": day_series(),
    }


def get_user_details(user_ids: list[str]) -> list[dict]:
    by_id = {u["user_id"]: u for u in _FUNNEL_USERS}
    out = []
    for uid in user_ids:
        u = by_id.get(uid)
        if not u:
            continue
        out.append({
            **u,
            "started_at": iso(u["started_at"]),
            "demo_timestamp": iso(u["demo_timestamp"]),
            "first_task_at": iso(u["first_task_at"]),
            "completed_at": iso(u["completed_at"]),
            "last_seen": iso(u["last_seen"]),
        })
    return out


# ---------------------------------------------------------------------------
# Dashboard stats / chart data
# ---------------------------------------------------------------------------

def build_dashboard_stats() -> dict:
    return {
        "total_groups": len(GROUPS),
        "active_groups_24h": 5,
        "active_groups_7d": 8,
        "active_groups_30d": len(GROUPS),
        "total_dms": len(DMS),
        "active_dms_7d": max(1, len(DMS) - 1),
        "active_dms_30d": len(DMS),
        "total_tasks": 736,
        "open_tasks": 62,
        "messages_24h": 214,
    }


def build_dashboard_chart_data() -> dict:
    days7 = [(NOW - timedelta(days=6 - i)).strftime("%a") for i in range(7)]
    hours24 = [f"{h:02d}:00" for h in range(24)]
    return {
        "messages_7d": {
            "labels": days7,
            "groups": [42, 58, 35, 71, 49, 63, 28],
            "dms": [18, 24, 15, 30, 21, 27, 12],
        },
        "messages_24h": {
            "labels": hours24,
            "groups": [0, 0, 0, 0, 0, 1, 2, 3, 4, 3, 2, 3, 4, 5, 4, 3, 2, 3, 4, 5, 4, 3, 2, 1],
            "dms": [0, 0, 0, 0, 1, 1, 2, 2, 3, 2, 3, 4, 3, 2, 3, 4, 3, 2, 3, 4, 5, 4, 3, 2],
        },
    }
