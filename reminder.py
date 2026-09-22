from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SERVICE_ROLE = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
RESEND_API_KEY = os.environ["RESEND_API_KEY"]
FROM_EMAIL = os.environ["REMINDER_FROM_EMAIL"]
APP_URL = os.environ["APP_URL"]

sb = create_client(SUPABASE_URL, SERVICE_ROLE)


def send_email(to_email: str, subject: str, html: str) -> bool:
    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html,
        },
        timeout=30,
    )
    print(to_email, subject, r.status_code, r.text[:200])
    return 200 <= r.status_code < 300


def already_sent(user_id: str, notification_type: str, notification_date: str) -> bool:
    rows = (
        sb.table("notification_log")
        .select("id")
        .eq("user_id", user_id)
        .eq("notification_type", notification_type)
        .eq("notification_date", notification_date)
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def mark_sent(user_id: str, notification_type: str, notification_date: str) -> None:
    sb.table("notification_log").upsert(
        {
            "user_id": user_id,
            "notification_type": notification_type,
            "notification_date": notification_date,
        },
        on_conflict="user_id,notification_type,notification_date",
    ).execute()


def has_any_daily_data(user_id: str, day_iso: str) -> bool:
    checks = [
        ("nutrition_logs", "logged_on"),
        ("daily_activity", "activity_date"),
        ("measurements", "measured_on"),
    ]
    for table, date_col in checks:
        rows = (
            sb.table(table)
            .select("user_id")
            .eq("user_id", user_id)
            .eq(date_col, day_iso)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return True
    return False


def handle_daily_logging_reminder(profile: dict, local_now: datetime) -> None:
    """A las 18:00 locales avisa solo si no existe ningún registro del día."""
    if local_now.hour != 18:
        return

    user_id = profile["user_id"]
    email = str(profile.get("email") or "").strip()
    if not email:
        return

    day_iso = local_now.date().isoformat()
    notification_type = "daily_no_data_18h"

    if already_sent(user_id, notification_type, day_iso):
        return
    if has_any_daily_data(user_id, day_iso):
        return

    subject = "Virgils Journey · aún no registras tu día"
    html = f"""
    <div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#111'>
      <h2 style='margin-bottom:8px'>Virgils Journey</h2>
      <p>Son cerca de las 18:00 y todavía no vemos registros de hoy.</p>
      <p>Si simplemente se te pasó, puedes registrar comidas, pasos, entrenamiento o tu medición ahora. También puedes completar días anteriores desde la app.</p>
      <p style='color:#666'>La idea es ayudarte a mantener continuidad, no exigir un día perfecto.</p>
      <p><a href='{APP_URL}' style='display:inline-block;background:#111;color:white;padding:12px 18px;border-radius:10px;text-decoration:none;font-weight:bold'>Registrar mi día</a></p>
    </div>
    """
    if send_email(email, subject, html):
        mark_sent(user_id, notification_type, day_iso)


def handle_weekly_measurement_reminder(profile: dict, local_now: datetime) -> None:
    """Mantiene el recordatorio semanal, una sola vez y a las 09:00 locales."""
    if local_now.hour != 9:
        return

    reminder_weekday = int(profile.get("reminder_weekday", 0) or 0)
    if reminder_weekday != local_now.date().weekday():
        return

    user_id = profile["user_id"]
    email = str(profile.get("email") or "").strip()
    if not email:
        return

    day_iso = local_now.date().isoformat()
    notification_type = "weekly_measurement"
    if already_sent(user_id, notification_type, day_iso):
        return

    last = (
        sb.table("measurements")
        .select("measured_on")
        .eq("user_id", user_id)
        .order("measured_on", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if last:
        last_date = datetime.fromisoformat(last[0]["measured_on"]).date()
        if (local_now.date() - last_date).days < 6:
            return

    subject = "Virgils Journey · tu medición semanal"
    html = f"""
    <div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#111'>
      <h2>Virgils Journey</h2>
      <p>Hoy es {WEEKDAYS[local_now.weekday()]} y corresponde registrar tu medición semanal.</p>
      <p>Un registro consistente mejora la calidad de tu tendencia y de la fecha proyectada.</p>
      <p><a href='{APP_URL}' style='display:inline-block;background:#111;color:white;padding:12px 18px;border-radius:10px;text-decoration:none;font-weight:bold'>Registrar medición</a></p>
    </div>
    """
    if send_email(email, subject, html):
        mark_sent(user_id, notification_type, day_iso)


def main() -> None:
    profiles = (
        sb.table("profiles")
        .select("user_id,email,reminder_weekday,timezone")
        .execute()
        .data
        or []
    )

    utc_now = datetime.now(ZoneInfo("UTC"))
    for profile in profiles:
        tz_name = str(profile.get("timezone") or "America/Santiago").strip() or "America/Santiago"
        try:
            local_now = utc_now.astimezone(ZoneInfo(tz_name))
        except Exception:
            local_now = utc_now.astimezone(ZoneInfo("America/Santiago"))

        handle_weekly_measurement_reminder(profile, local_now)
        handle_daily_logging_reminder(profile, local_now)


if __name__ == "__main__":
    main()
