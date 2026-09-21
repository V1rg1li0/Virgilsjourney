from __future__ import annotations

import truststore
truststore.inject_into_ssl()

from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from analytics import build_projection, bmi, tdee_estimate
from db import configured, client, sign_in, sign_up, sign_out
from ai_nutrition import estimate_with_gemini

st.set_page_config(page_title="Virgils Journey", page_icon="🏃", layout="centered")

st.markdown("""
<style>
:root { --vj:#6E44FF; --vj2:#00A6A6; --ink:#172033; --muted:#6B7280; --card:#ffffff; }
[data-testid="stAppViewContainer"]{background:linear-gradient(180deg,#F5F7FF 0%,#F8FBFC 100%)}
.block-container{max-width:760px;padding-top:1rem;padding-bottom:5rem}
.vj-hero{padding:18px 18px 16px;border-radius:24px;background:linear-gradient(135deg,#6E44FF,#8A5CFF 55%,#2CB7B0);color:white;box-shadow:0 12px 30px rgba(71,55,180,.25)}
.vj-title{font-size:30px;font-weight:900;line-height:1.05;margin:0}.vj-sub{opacity:.9;margin-top:7px;font-size:14px}
.vj-card{background:white;border:1px solid #E9EAF1;border-radius:20px;padding:16px;box-shadow:0 6px 18px rgba(30,42,70,.06);margin:10px 0}
.vj-kpi{font-size:28px;font-weight:900;color:#172033}.vj-label{color:#6B7280;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.vj-good{color:#0F9D76}.vj-warn{color:#D97706}.vj-bad{color:#D64545}
div[data-testid="stMetric"]{background:white;border:1px solid #E9EAF1;padding:12px;border-radius:18px}
.stButton>button{border-radius:14px;font-weight:800;min-height:44px}
.stTextInput input,.stNumberInput input,.stDateInput input{border-radius:12px}
@media (max-width:640px){.block-container{padding-left:.75rem;padding-right:.75rem}.vj-title{font-size:26px}}
</style>
""", unsafe_allow_html=True)

WEEKDAYS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]


def hero(sub="Control semanal de progreso, hábitos y nutrición"):
    st.markdown(f"<div class='vj-hero'><div class='vj-title'>Virgils Journey</div><div class='vj-sub'>{sub}</div></div>", unsafe_allow_html=True)


def auth_screen():
    hero("Tu viaje, medido con datos y proyecciones prudentes")
    if not configured():
        st.error("Falta configurar Supabase. Revisa README.md y .streamlit/secrets.example.toml.")
        st.stop()
    tab1, tab2 = st.tabs(["Ingresar", "Crear cuenta"])
    with tab1:
        with st.form("login"):
            email = st.text_input("Correo")
            password = st.text_input("Contraseña", type="password")
            ok = st.form_submit_button("Entrar", use_container_width=True)
        if ok:
            try:
                sign_in(email.strip(), password)
                st.rerun()
            except Exception as e:
                st.error(f"No fue posible iniciar sesión: {e}")
    with tab2:
        with st.form("signup"):
            email = st.text_input("Correo", key="su_email")
            p1 = st.text_input("Contraseña (mín. 8 caracteres)", type="password", key="su_p1")
            p2 = st.text_input("Repite contraseña", type="password", key="su_p2")
            ok = st.form_submit_button("Crear cuenta", use_container_width=True)
        if ok:
            if p1 != p2 or len(p1) < 8:
                st.warning("Revisa la contraseña.")
            else:
                try:
                    res = sign_up(email.strip(), p1)
                    if res.session:
                        st.session_state.access_token = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        st.session_state.user_id = res.user.id
                        st.session_state.email = res.user.email
                        st.rerun()
                    else:
                        st.success("Cuenta creada. Revisa tu correo para confirmar y luego inicia sesión.")
                except Exception as e:
                    st.error(f"No fue posible crear la cuenta: {e}")
    st.stop()


def get_profile(sb, uid):
    r = sb.table("profiles").select("*").eq("user_id", uid).limit(1).execute()
    return r.data[0] if r.data else None


def load_measurements(sb, uid):
    r = sb.table("measurements").select("*").eq("user_id", uid).order("measured_on").execute()
    return pd.DataFrame(r.data or [])


def load_nutrition(sb, uid, day=None):
    q = sb.table("nutrition_logs").select("*").eq("user_id", uid)
    if day:
        q = q.eq("logged_on", str(day))
    r = q.order("created_at").execute()
    return pd.DataFrame(r.data or [])


def onboarding(sb, uid, email):
    hero("Configura tu punto de partida")
    st.info("Tu primera medición define el día habitual del recordatorio semanal. Puedes cambiarlo después.")
    with st.form("onboarding"):
        c1, c2 = st.columns(2)
        with c1:
            age = st.number_input("Edad", 18, 100, 41)
            height = st.number_input("Estatura (cm)", 120.0, 230.0, 180.0, 0.5)
            weight = st.number_input("Peso actual (kg)", 35.0, 300.0, 108.0, 0.1)
            goal = st.number_input("Meta de peso (kg)", 35.0, 300.0, 95.0, 0.1)
        with c2:
            chest = st.number_input("Pecho (cm)", 40.0, 220.0, 119.0, 0.5)
            waist = st.number_input("Cintura (cm)", 40.0, 220.0, 112.0, 0.5)
            neck = st.number_input("Cuello (cm)", 20.0, 80.0, 44.0, 0.5)
            hip = st.number_input("Cadera (cm)", 40.0, 220.0, 107.0, 0.5)
        sex = st.selectbox("Sexo para estimación metabólica (opcional)", ["No indicar", "Hombre", "Mujer"])
        activity = st.selectbox("Actividad habitual (opcional)", ["Sedentario","Ligero","Moderado","Alto","Muy alto"])
        reminder = st.selectbox("Día de recordatorio semanal", WEEKDAYS, index=date.today().weekday())
        consent = st.checkbox("Entiendo que las proyecciones son estimaciones orientativas y no reemplazan atención médica.")
        submit = st.form_submit_button("Comenzar mi Journey", use_container_width=True)
    if submit:
        if not consent:
            st.warning("Confirma la nota de uso para continuar.")
            return
        sb.table("profiles").insert({
            "user_id": uid, "email": email, "age": int(age), "height_cm": float(height),
            "goal_weight_kg": float(goal), "reminder_weekday": WEEKDAYS.index(reminder),
            "sex": None if sex == "No indicar" else sex, "activity_level": activity,
            "timezone": "America/Santiago"
        }).execute()
        sb.table("measurements").insert({
            "user_id": uid, "measured_on": str(date.today()), "weight_kg": float(weight),
            "chest_cm": float(chest), "waist_cm": float(waist), "neck_cm": float(neck), "hip_cm": float(hip),
            "notes": "Medición inicial"
        }).execute()
        st.success("Journey iniciado.")
        st.rerun()


def weekly_due(df: pd.DataFrame) -> bool:
    if df.empty:
        return True
    last = pd.to_datetime(df["measured_on"]).max().date()
    return (date.today() - last).days >= 7


def dashboard(sb, uid, profile, measurements):
    hero()
    if measurements.empty:
        st.warning("No hay mediciones. Registra una para comenzar.")
        return
    measurements = measurements.copy()
    measurements["measured_on"] = pd.to_datetime(measurements["measured_on"])
    last = measurements.sort_values("measured_on").iloc[-1]
    projection = build_projection(measurements, float(profile["goal_weight_kg"]), float(profile["height_cm"]))

    if weekly_due(measurements):
        st.warning("📏 Tu medición semanal está pendiente. Regístrala hoy para mantener la proyección actualizada.")
    else:
        st.success("✅ Medición semanal al día.")

    c1,c2,c3 = st.columns(3)
    c1.metric("Peso", f"{float(last['weight_kg']):.1f} kg")
    c2.metric("Meta", f"{float(profile['goal_weight_kg']):.1f} kg")
    c3.metric("Progreso", f"{(projection.progress_pct or 0):.0f}%")

    st.progress(min(max((projection.progress_pct or 0)/100, 0.0), 1.0))

    if projection.ready:
        c1,c2 = st.columns(2)
        pace_txt = "S/D" if projection.pace_kg_week is None else f"{projection.pace_kg_week:+.2f} kg/sem"
        c1.metric("Ritmo observado", pace_txt)
        c2.metric("Fecha estimada", projection.projected_date.strftime("%d-%m-%Y") if projection.projected_date else "Aún no estimable")
        st.caption(projection.message)
        if projection.pace_kg_week is not None:
            loss = abs(projection.pace_kg_week) if projection.pace_kg_week < 0 else 0
            if 0.45 <= loss <= 0.91:
                st.success("El ritmo observado está dentro del rango gradual de 1–2 lb/semana citado por CDC.")
            elif loss > 0.91:
                st.warning("Tu ritmo observado supera 2 lb/semana. La app no asume que ese ritmo sea sostenible; considera revisarlo con un profesional de salud.")
    else:
        st.info(projection.message)

    # chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=measurements["measured_on"], y=measurements["weight_kg"], mode="lines+markers", name="Peso"))
    fig.add_hline(y=float(profile["goal_weight_kg"]), line_dash="dash", annotation_text="Meta")
    fig.update_layout(height=320, margin=dict(l=5,r=5,t=25,b=5), legend_orientation="h", yaxis_title="kg", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Medidas corporales")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Pecho", f"{float(last['chest_cm']):.1f} cm")
    c2.metric("Cintura", f"{float(last['waist_cm']):.1f} cm")
    c3.metric("Cuello", f"{float(last['neck_cm']):.1f} cm")
    c4.metric("Cadera", f"{float(last['hip_cm']):.1f} cm")
    st.caption(f"IMC actual: {projection.bmi_current:.1f} · IMC en meta: {projection.bmi_goal:.1f}" if projection.bmi_current else "")


def measurement_form(sb, uid, measurements):
    st.markdown("## Nueva medición")
    defaults = {"weight_kg":108.0,"chest_cm":119.0,"waist_cm":112.0,"neck_cm":44.0,"hip_cm":107.0}
    if not measurements.empty:
        row = measurements.sort_values("measured_on").iloc[-1]
        for k in defaults:
            defaults[k] = float(row[k])
    with st.form("measure"):
        day = st.date_input("Fecha", date.today())
        weight = st.number_input("Peso (kg)", 35.0, 300.0, defaults["weight_kg"], 0.1)
        c1,c2 = st.columns(2)
        with c1:
            chest = st.number_input("Pecho (cm)", 40.0, 220.0, defaults["chest_cm"], 0.5)
            waist = st.number_input("Cintura (cm)", 40.0, 220.0, defaults["waist_cm"], 0.5)
        with c2:
            neck = st.number_input("Cuello (cm)", 20.0, 80.0, defaults["neck_cm"], 0.5)
            hip = st.number_input("Cadera (cm)", 40.0, 220.0, defaults["hip_cm"], 0.5)
        notes = st.text_area("Notas (opcional)", placeholder="Sueño, entrenamiento, viaje, retención de líquidos, etc.")
        ok = st.form_submit_button("Guardar medición", use_container_width=True)
    if ok:
        sb.table("measurements").upsert({
            "user_id":uid,"measured_on":str(day),"weight_kg":float(weight),"chest_cm":float(chest),
            "waist_cm":float(waist),"neck_cm":float(neck),"hip_cm":float(hip),"notes":notes
        }, on_conflict="user_id,measured_on").execute()
        st.success("Medición guardada.")
        st.rerun()


def nutrition_page(sb, uid, profile, measurements):
    st.markdown("## Nutrición")
    st.caption("Registra lo que comiste. El análisis con IA es una estimación, no una medición de laboratorio.")
    today = date.today()
    logs = load_nutrition(sb, uid, today)
    last_weight = float(measurements.sort_values("measured_on").iloc[-1]["weight_kg"]) if not measurements.empty else None
    if last_weight:
        tdee = tdee_estimate(last_weight, float(profile["height_cm"]), int(profile["age"]), profile.get("sex") or "", profile.get("activity_level") or "Sedentario")
        if tdee:
            st.info(f"Gasto energético diario estimado (Mifflin–St Jeor + actividad): **{tdee:.0f} kcal/día**. Úsalo solo como referencia aproximada.")

    text = st.text_area("¿Qué comiste?", placeholder="Ej.: 200 g de pechuga de pollo, 1 taza de arroz, ensalada y un yogur")
    ai_enabled = bool(st.secrets.get("GEMINI_API_KEY", ""))
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Estimar con IA", use_container_width=True, disabled=not ai_enabled):
            if not text.strip(): st.warning("Escribe una comida primero.")
            else:
                try:
                    est = estimate_with_gemini(text, st.secrets["GEMINI_API_KEY"], st.secrets.get("GEMINI_MODEL","gemini-3.7-flash"))
                    st.session_state.ai_food = est
                except Exception as e:
                    st.error(f"No fue posible estimar: {e}")
    with c2:
        st.caption("IA disponible" if ai_enabled else "Configura GEMINI_API_KEY para usar IA")

    est = st.session_state.get("ai_food", {})
    with st.form("food"):
        calories = st.number_input("Calorías (kcal)", 0, 10000, int(est.get("calories_kcal",0) or 0))
        protein = st.number_input("Proteína (g)", 0.0, 1000.0, float(est.get("protein_g",0) or 0), 1.0)
        carbs = st.number_input("Carbohidratos (g)", 0.0, 1500.0, float(est.get("carbs_g",0) or 0), 1.0)
        fat = st.number_input("Grasas (g)", 0.0, 1000.0, float(est.get("fat_g",0) or 0), 1.0)
        if est.get("summary"): st.caption(est["summary"])
        ok = st.form_submit_button("Agregar al día", use_container_width=True)
    if ok:
        sb.table("nutrition_logs").insert({"user_id":uid,"logged_on":str(today),"description":text or "Registro manual",
            "calories_kcal":int(calories),"protein_g":float(protein),"carbs_g":float(carbs),"fat_g":float(fat),"ai_estimated":bool(est)}).execute()
        st.session_state.pop("ai_food",None)
        st.rerun()

    logs = load_nutrition(sb, uid, today)
    if not logs.empty:
        st.markdown("### Hoy")
        c1,c2 = st.columns(2)
        c1.metric("Calorías", f"{logs['calories_kcal'].fillna(0).sum():.0f} kcal")
        c2.metric("Proteína", f"{logs['protein_g'].fillna(0).sum():.0f} g")
        st.dataframe(logs[["description","calories_kcal","protein_g","carbs_g","fat_g"]], use_container_width=True, hide_index=True)


def settings_page(sb, uid, profile):
    st.markdown("## Ajustes")
    with st.form("settings"):
        goal = st.number_input("Meta de peso (kg)", 35.0, 300.0, float(profile["goal_weight_kg"]), 0.1)
        reminder = st.selectbox("Día de recordatorio", WEEKDAYS, index=int(profile.get("reminder_weekday") or 0))
        activity = st.selectbox("Actividad", ["Sedentario","Ligero","Moderado","Alto","Muy alto"], index=["Sedentario","Ligero","Moderado","Alto","Muy alto"].index(profile.get("activity_level") or "Sedentario"))
        ok = st.form_submit_button("Guardar")
    if ok:
        sb.table("profiles").update({"goal_weight_kg":float(goal),"reminder_weekday":WEEKDAYS.index(reminder),"activity_level":activity}).eq("user_id",uid).execute()
        st.success("Ajustes guardados.")
        st.rerun()
    st.markdown("### Metodología")
    st.write("La proyección se activa con al menos 4 mediciones distribuidas en ~4 semanas. Usa una tendencia robusta de peso (mediana de pendientes entre pares de puntos), y se actualiza con hasta las últimas 8 mediciones.")
    st.write("El rango de 1–2 lb/semana se muestra solo como referencia de pérdida gradual citada por CDC. La fecha objetivo es una estimación y puede cambiar por líquidos, adherencia, enfermedad, medicamentos, sueño y otros factores.")
    if st.button("Cerrar sesión", use_container_width=True):
        sign_out(); st.rerun()


# --- app ---
# Inicializa las claves de sesión para evitar KeyError en reruns parciales
for _key in ["access_token", "refresh_token", "user_id", "email"]:
    st.session_state.setdefault(_key, None)


def ensure_authenticated_session() -> bool:
    """Valida la sesión y recupera user_id/email si faltan."""
    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")

    if not access_token:
        return False

    # Si ya tenemos el usuario completo, no hacemos llamadas extra
    if st.session_state.get("user_id"):
        return True

    # Hay token, pero falta user_id: reconstruimos la sesión desde Supabase
    try:
        sb_tmp = client()

        # client() ya intenta set_session(access, refresh). Si refresh_token
        # también existe, get_user() puede recuperar el usuario autenticado.
        if access_token and refresh_token:
            sb_tmp.auth.set_session(access_token, refresh_token)

        user_response = sb_tmp.auth.get_user()
        user = getattr(user_response, "user", None)

        if user and getattr(user, "id", None):
            st.session_state["user_id"] = user.id
            st.session_state["email"] = getattr(user, "email", "") or ""
            return True

    except Exception:
        pass

    # Si no pudimos reconstruirla, limpiamos la sesión incompleta
    for _key in ["access_token", "refresh_token", "user_id", "email"]:
        st.session_state.pop(_key, None)

    return False


if not ensure_authenticated_session():
    auth_screen()
    st.stop()

# Usuario autenticado
sb = client()
uid = st.session_state.get("user_id")
email = st.session_state.get("email", "") or ""

if not uid:
    st.error("No fue posible recuperar la sesión. Vuelve a iniciar sesión.")
    for _key in ["access_token", "refresh_token", "user_id", "email"]:
        st.session_state.pop(_key, None)
    st.stop()

profile = get_profile(sb, uid)
if not profile:
    onboarding(sb, uid, email)
    st.stop()

measurements = load_measurements(sb, uid)

page = st.radio(
    "",
    ["Inicio", "Medición", "Nutrición", "Ajustes"],
    horizontal=True,
    label_visibility="collapsed",
)

if page == "Inicio":
    dashboard(sb, uid, profile, measurements)
elif page == "Medición":
    measurement_form(sb, uid, measurements)
elif page == "Nutrición":
    nutrition_page(sb, uid, profile, measurements)
else:
    settings_page(sb, uid, profile)
