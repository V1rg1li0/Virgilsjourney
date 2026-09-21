from __future__ import annotations
import os
from datetime import date, timedelta
import requests
from supabase import create_client

WEEKDAYS = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]

SUPABASE_URL=os.environ["SUPABASE_URL"]
SERVICE_ROLE=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
RESEND_API_KEY=os.environ["RESEND_API_KEY"]
FROM_EMAIL=os.environ["REMINDER_FROM_EMAIL"]
APP_URL=os.environ["APP_URL"]

sb=create_client(SUPABASE_URL,SERVICE_ROLE)
today=date.today()
profiles=sb.table("profiles").select("user_id,email,reminder_weekday").execute().data or []

for p in profiles:
    if int(p.get("reminder_weekday",0)) != today.weekday():
        continue
    last=sb.table("measurements").select("measured_on").eq("user_id",p["user_id"]).order("measured_on",desc=True).limit(1).execute().data or []
    if last:
        last_date=date.fromisoformat(last[0]["measured_on"])
        if (today-last_date).days < 6:
            continue
    subject="Virgils Journey · tu medición semanal"
    html=f"""<div style='font-family:Arial;max-width:560px;margin:auto'>
    <h2 style='color:#6E44FF'>Virgils Journey</h2>
    <p>Hoy es {WEEKDAYS[today.weekday()]} y corresponde registrar tu medición semanal.</p>
    <p>Un registro consistente mejora la calidad de tu tendencia y de la fecha proyectada.</p>
    <p><a href='{APP_URL}' style='background:#6E44FF;color:white;padding:12px 18px;border-radius:10px;text-decoration:none'>Registrar medición</a></p>
    </div>"""
    r=requests.post("https://api.resend.com/emails",headers={"Authorization":f"Bearer {RESEND_API_KEY}","Content-Type":"application/json"},json={"from":FROM_EMAIL,"to":[p["email"]],"subject":subject,"html":html},timeout=30)
    print(p["email"], r.status_code, r.text[:200])
