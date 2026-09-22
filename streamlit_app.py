
from __future__ import annotations

import sys
import html
import base64
from pathlib import Path

# En equipos Windows corporativos puede ser necesario usar el almacén de certificados del sistema.
# En Streamlit Cloud/Linux este bloque no hace nada.
if sys.platform == "win32":
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass

from datetime import date, datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo
from io import BytesIO
from uuid import uuid4
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from PIL import Image, ImageOps

from analytics import (
    build_projection,
    bmi,
    tdee_estimate,
    daily_expenditure_with_activity,
    behavior_projection_from_energy_balance,
)
from db import configured, client, sign_in, sign_up, sign_out, sign_in_with_google_tokens
from ai_nutrition import estimate_nutrition, analyze_daily_balance

st.set_page_config(page_title="Virgils Journey", page_icon="⚫", layout="centered")

st.markdown("""
<style>
:root{
    --vj:#111111;
    --vj2:#2B2B2B;
    --ink:#111111;
    --muted:#6E6E6E;
    --soft:#F4F4F4;
    --soft2:#EAEAEA;
    --border:#D8D8D8;
    --card:#FFFFFF;
}

/* Fondo general */
[data-testid="stAppViewContainer"]{
    background:linear-gradient(180deg,#F7F7F7 0%,#EFEFEF 100%);
    color:#111111;
}

.block-container{
    max-width:760px;
    padding-top:1rem;
    padding-bottom:5rem;
}

/* Hero / marca */
.vj-hero{
    display:flex;
    align-items:center;
    gap:18px;
    padding:18px 20px;
    border-radius:22px;
    background:linear-gradient(145deg,#FFFFFF 0%,#F2F2F2 100%);
    color:#111111;
    border:1px solid #D8D8D8;
    box-shadow:0 10px 28px rgba(0,0,0,.10);
    margin-bottom:10px;
}
.vj-logo{
    width:92px;
    height:92px;
    object-fit:contain;
    border-radius:16px;
    background:#FFFFFF;
    border:1px solid #E2E2E2;
    padding:5px;
}
.vj-brand-copy{
    min-width:0;
}
.vj-title{
    font-size:30px;
    font-weight:900;
    line-height:1.05;
    margin:0;
    color:#111111;
    letter-spacing:-0.02em;
}
.vj-sub{
    color:#5E5E5E;
    margin-top:7px;
    font-size:14px;
    line-height:1.4;
}

/* Tarjetas */
.vj-card{
    background:#FFFFFF;
    border:1px solid #DCDCDC;
    border-radius:18px;
    padding:16px;
    box-shadow:0 5px 16px rgba(0,0,0,.05);
    margin:10px 0;
}
.vj-kpi{
    font-size:28px;
    font-weight:900;
    color:#111111;
}
.vj-label{
    color:#707070;
    font-size:12px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.04em;
}
.vj-good,.vj-warn,.vj-bad{color:#333333}

/* Métricas */
div[data-testid="stMetric"]{
    background:#FFFFFF;
    border:1px solid #D8D8D8;
    padding:12px;
    border-radius:16px;
    box-shadow:0 3px 10px rgba(0,0,0,.035);
}
div[data-testid="stMetricValue"]{
    color:#111111;
}

/* Botones */
.stButton>button,
.stLinkButton>a{
    border-radius:12px !important;
    font-weight:800 !important;
    min-height:44px;
    background:#111111 !important;
    color:#FFFFFF !important;
    border:1px solid #111111 !important;
}
.stButton>button:hover,
.stLinkButton>a:hover{
    background:#2E2E2E !important;
    border-color:#2E2E2E !important;
    color:#FFFFFF !important;
}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea{
    border-radius:11px !important;
    border-color:#CDCDCD !important;
    background:#FFFFFF !important;
}
.stSelectbox div[data-baseweb="select"] > div{
    border-color:#CDCDCD !important;
    background:#FFFFFF !important;
}

/* Alertas en escala de grises */
div[data-testid="stAlert"]{
    border-radius:14px;
    border:1px solid #D6D6D6;
    background:#F5F5F5;
    color:#222222;
}
div[data-testid="stAlert"] svg{
    color:#333333 !important;
}

/* Barra de progreso */
div[data-testid="stProgress"] > div > div > div{
    background:#111111 !important;
}

/* Tabs / navegación */
div[data-testid="stTabs"]{
    margin-top:.35rem;
    margin-bottom:.65rem;
}
div[data-testid="stTabs"] button[role="tab"]{
    font-weight:800;
    font-size:14px;
    padding:.65rem .85rem;
    color:#6A6A6A;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
    color:#111111 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"]{
    background-color:#111111 !important;
}

/* Separadores */
hr{
    border-color:#D8D8D8 !important;
}

/* Tablas */
[data-testid="stDataFrame"]{
    border:1px solid #D8D8D8;
    border-radius:12px;
    overflow:hidden;
}

/* Links */
a{
    color:#222222;
}

/* Guía rápida / onboarding */
.vj-guide-shell{
    background:#FFFFFF;
    border:1px solid #D8D8D8;
    border-radius:22px;
    padding:24px 22px;
    box-shadow:0 10px 28px rgba(0,0,0,.08);
    margin:10px 0 14px;
}
.vj-guide-kicker{
    color:#777777;
    font-size:12px;
    font-weight:900;
    text-transform:uppercase;
    letter-spacing:.10em;
}
.vj-guide-title{
    color:#111111;
    font-size:27px;
    font-weight:900;
    line-height:1.12;
    margin-top:8px;
    letter-spacing:-.02em;
}
.vj-guide-copy{
    color:#4F4F4F;
    font-size:15px;
    line-height:1.6;
    margin-top:12px;
}
.vj-quote{
    color:#111111;
    font-size:21px;
    font-weight:800;
    line-height:1.55;
    text-align:center;
    padding:14px 4px 6px;
}
.vj-quote-author{
    color:#666666;
    font-size:14px;
    font-weight:800;
    text-align:center;
    margin-top:10px;
}
.vj-guide-pills{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:7px;
    margin-top:16px;
}
.vj-guide-pill{
    background:#F3F3F3;
    border:1px solid #E0E0E0;
    border-radius:12px;
    padding:9px 7px;
    text-align:center;
    color:#555555;
    font-size:11px;
    font-weight:800;
}
.vj-guide-step{
    display:flex;
    align-items:flex-start;
    gap:12px;
    margin-top:14px;
    padding:13px;
    border-radius:14px;
    background:#F6F6F6;
    border:1px solid #E2E2E2;
}
.vj-guide-icon{
    width:36px;
    height:36px;
    min-width:36px;
    border-radius:50%;
    background:#111111;
    color:#FFFFFF;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:17px;
    font-weight:900;
}
.vj-guide-step-title{
    color:#111111;
    font-size:14px;
    font-weight:900;
}
.vj-guide-step-copy{
    color:#606060;
    font-size:13px;
    line-height:1.45;
    margin-top:3px;
}

/* Mobile */
@media (max-width:640px){
    .block-container{
        padding-left:.75rem;
        padding-right:.75rem;
    }
    .vj-hero{
        gap:12px;
        padding:14px;
    }
    .vj-logo{
        width:72px;
        height:72px;
    }
    .vj-title{
        font-size:24px;
    }
    .vj-sub{
        font-size:12.5px;
    }
    div[data-testid="stTabs"] button[role="tab"]{
        font-size:12px;
        padding:.55rem .45rem;
    }
}


/* Métricas compactas para evitar textos cortados */
.vj-metrics-grid{
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:14px;
    margin:8px 0 14px 0;
}
.vj-metric-card{
    min-width:0;
    padding:16px 16px 14px 16px;
    border:1px solid var(--border);
    border-radius:18px;
    background:rgba(255,255,255,.94);
    box-shadow:0 5px 18px rgba(0,0,0,.06);
}
.vj-metric-label{font-size:.90rem;color:#454545;margin-bottom:6px;line-height:1.2;}
.vj-metric-value{font-size:1.72rem;font-weight:700;letter-spacing:-.03em;line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.vj-metric-note{font-size:.76rem;color:var(--muted);margin-top:7px;line-height:1.25;}
.vj-coach-card{
    border:1px solid var(--border);border-radius:20px;background:#fff;
    padding:18px 18px 14px 18px;margin:12px 0 10px 0;
    box-shadow:0 7px 22px rgba(0,0,0,.06);
}
.vj-coach-title{font-size:1.08rem;font-weight:750;margin-bottom:6px;}
.vj-coach-text{font-size:.94rem;line-height:1.45;color:#2c2c2c;}
.vj-progress-label{display:flex;justify-content:space-between;gap:12px;font-size:.84rem;margin-bottom:5px;color:#444;}
.vj-progress-track{width:100%;height:9px;background:#ECECEC;border-radius:999px;overflow:hidden;margin-bottom:12px;}
.vj-progress-fill{height:100%;background:#222;border-radius:999px;}
@media (max-width: 680px){
    .vj-metrics-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
    .vj-metric-value{font-size:1.45rem;}
}

</style>
""", unsafe_allow_html=True)

WEEKDAYS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

PHOTO_BUCKET = "progress-photos"
MAX_PHOTO_BYTES = 6 * 1024 * 1024
PHOTO_MAX_SIDE = 1600
DONATION_WHATSAPP = "56985827304"


def hero(sub="Control semanal de progreso, hábitos y nutrición"):
    logo_path = Path(__file__).resolve().parent / "assets" / "logovj.png"

    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
        logo_html = (
            f"<img class='vj-logo' src='data:image/png;base64,{logo_b64}' "
            "alt='Virgils Journey logo'>"
        )
    else:
        logo_html = (
            "<div class='vj-logo' style='display:flex;align-items:center;"
            "justify-content:center;font-size:34px;font-weight:900;'>VJ</div>"
        )

    st.markdown(
        f"""
        <div class='vj-hero'>
            {logo_html}
            <div class='vj-brand-copy'>
                <div class='vj-title'>Virgils Journey</div>
                <div class='vj-sub'>{sub}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def sync_google_session_to_supabase():
    """
    Si Streamlit ya autenticó al usuario con Google, intercambia el ID token
    por una sesión Supabase para conservar las políticas RLS existentes.
    """
    try:
        is_google_logged = bool(getattr(st.user, "is_logged_in", False))
    except Exception:
        is_google_logged = False

    if not is_google_logged:
        return False

    if st.session_state.get("access_token") and st.session_state.get("user_id"):
        return True

    try:
        id_token = st.user.tokens.get("id")
        access_token = st.user.tokens.get("access")

        sign_in_with_google_tokens(
            id_token=id_token,
            access_token=access_token,
        )
        return True
    except Exception as e:
        st.error(
            "Google autenticó la cuenta, pero no fue posible crear la sesión "
            f"en Supabase: {e}"
        )
        return False


def auth_screen():
    hero("Tu viaje, medido con datos y proyecciones prudentes")

    if not configured():
        st.error("Falta configurar Supabase. Revisa los Secrets de la aplicación.")
        st.stop()

    # Si el navegador acaba de volver del login de Google, sincronizamos
    # automáticamente esa identidad con Supabase.
    if sync_google_session_to_supabase():
        st.rerun()

    st.markdown("### Accede a tu Journey")

    if st.button(
        "G  Continuar con Google",
        use_container_width=True,
        type="primary",
        key="google_login",
    ):
        st.login("google")

    st.caption("O continúa con correo y contraseña")
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
            p1 = st.text_input(
                "Contraseña (mín. 8 caracteres)",
                type="password",
                key="su_p1",
            )
            p2 = st.text_input(
                "Repite contraseña",
                type="password",
                key="su_p2",
            )
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
                        st.session_state.auth_provider = "password"
                        st.rerun()
                    else:
                        st.success(
                            "Cuenta creada. Revisa tu correo para confirmar "
                            "y luego inicia sesión."
                        )
                except Exception as e:
                    st.error(f"No fue posible crear la cuenta: {e}")

    st.stop()

def get_profile(sb, uid):
    r = sb.table("profiles").select("*").eq("user_id", uid).limit(1).execute()
    return r.data[0] if r.data else None


def preferred_name(profile: dict | None, fallback: str = "") -> str:
    """Nombre que Virgils Journey usa para hablarle al usuario."""
    profile = profile or {}
    display_name = str(profile.get("display_name") or "").strip()
    full_name = str(profile.get("full_name") or "").strip()
    fallback = str(fallback or "").strip()
    return display_name or full_name or fallback or "viajero"


def _parse_profile_time(value, default: dt_time) -> dt_time:
    if isinstance(value, dt_time):
        return value.replace(second=0, microsecond=0)
    text = str(value or "").strip()
    if not text:
        return default
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            pass
    return default


def _format_hhmm(value) -> str:
    if isinstance(value, dt_time):
        return value.strftime("%H:%M")
    return _parse_profile_time(value, dt_time(8, 0)).strftime("%H:%M")


def _local_now(profile: dict | None) -> datetime:
    profile = profile or {}
    tz_name = str(profile.get("timezone") or "America/Santiago").strip() or "America/Santiago"
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now()


def _meal_window(profile: dict | None) -> dict:
    profile = profile or {}
    configured = (
        profile.get("eating_window_start") is not None
        and profile.get("eating_window_end") is not None
        and profile.get("intermittent_fasting") is not None
    )
    fasting = bool(profile.get("intermittent_fasting")) if profile.get("intermittent_fasting") is not None else False
    start = _parse_profile_time(profile.get("eating_window_start"), dt_time(8, 0))
    end = _parse_profile_time(profile.get("eating_window_end"), dt_time(21, 0))
    return {"configured": configured, "fasting": fasting, "start": start, "end": end}


def _minutes_since_midnight(t: dt_time) -> int:
    return t.hour * 60 + t.minute


def _meal_window_status(profile: dict | None, now: datetime | None = None) -> dict:
    window = _meal_window(profile)
    now = now or _local_now(profile)
    current = now.timetz().replace(tzinfo=None, second=0, microsecond=0)
    cur_m = _minutes_since_midnight(current)
    start_m = _minutes_since_midnight(window["start"])
    end_m = _minutes_since_midnight(window["end"])

    # Ventana normal (ej. 08:00-21:00) o nocturna que cruza medianoche.
    if start_m == end_m:
        status = "within"
        elapsed = 1.0
    elif start_m < end_m:
        if cur_m < start_m:
            status = "before"
            elapsed = 0.0
        elif cur_m <= end_m:
            status = "within"
            elapsed = (cur_m - start_m) / max(1, end_m - start_m)
        else:
            status = "after"
            elapsed = 1.0
    else:
        # Ej. 18:00-02:00
        in_window = cur_m >= start_m or cur_m <= end_m
        if in_window:
            status = "within"
            total = (24 * 60 - start_m) + end_m
            passed = (cur_m - start_m) if cur_m >= start_m else (24 * 60 - start_m) + cur_m
            elapsed = passed / max(1, total)
        else:
            status = "before"
            elapsed = 0.0

    return {
        **window,
        "now": now,
        "current_time": current,
        "status": status,
        "elapsed_fraction": min(1.0, max(0.0, float(elapsed))),
        "window_label": f"{window['start'].strftime('%H:%M')}–{window['end'].strftime('%H:%M')}",
    }


def load_measurements(sb, uid):
    r = sb.table("measurements").select("*").eq("user_id", uid).order("measured_on").execute()
    return pd.DataFrame(r.data or [])


def load_nutrition(sb, uid, day=None):
    q = sb.table("nutrition_logs").select("*").eq("user_id", uid)
    if day:
        q = q.eq("logged_on", str(day))
    r = q.order("created_at").execute()
    return pd.DataFrame(r.data or [])


def load_activity(sb, uid, day=None):
    q = sb.table("daily_activity").select("*").eq("user_id", uid)
    if day:
        q = q.eq("activity_date", str(day))
    r = q.order("activity_date").execute()
    return pd.DataFrame(r.data or [])


def _latest_weight(measurements: pd.DataFrame) -> float | None:
    if measurements is None or measurements.empty:
        return None
    row = measurements.sort_values("measured_on").iloc[-1]
    return float(row["weight_kg"])


def _weight_on_or_before(measurements: pd.DataFrame, day: date) -> float | None:
    """Devuelve el peso más cercano disponible en o antes del día solicitado."""
    if measurements is None or measurements.empty:
        return None
    df = measurements.copy()
    df["measured_on"] = pd.to_datetime(df["measured_on"]).dt.date
    prior = df[df["measured_on"] <= day].sort_values("measured_on")
    if not prior.empty:
        return float(prior.iloc[-1]["weight_kg"])
    # Si el usuario carga datos anteriores a su primera medición, usamos la primera
    # medición conocida como aproximación en lugar de bloquear el registro.
    return float(df.sort_values("measured_on").iloc[0]["weight_kg"])


def _weekly_behavior_summary(sb, uid, profile, measurements, days=7):
    """
    Resume nutrición + pasos + fuerza para los últimos N días.
    No interpreta la ausencia de comida como 0 kcal: solo usa días con
    al menos un registro nutricional.
    """
    all_nutrition = load_nutrition(sb, uid)
    all_activity = load_activity(sb, uid)

    end_day = _local_now(profile).date()
    start_day = end_day - timedelta(days=days - 1)
    current_weight = _latest_weight(measurements)

    if current_weight is None or all_nutrition.empty:
        return None

    ndf = all_nutrition.copy()
    ndf["logged_on"] = pd.to_datetime(ndf["logged_on"]).dt.date
    ndf = ndf[(ndf["logged_on"] >= start_day) & (ndf["logged_on"] <= end_day)]
    if ndf.empty:
        return None

    daily_food = (
        ndf.groupby("logged_on", as_index=False)
        .agg(
            calories_kcal=("calories_kcal", "sum"),
            protein_g=("protein_g", "sum"),
            carbs_g=("carbs_g", "sum"),
            fat_g=("fat_g", "sum"),
        )
    )

    activity_by_day = {}
    if not all_activity.empty:
        adf = all_activity.copy()
        adf["activity_date"] = pd.to_datetime(adf["activity_date"]).dt.date
        adf = adf[(adf["activity_date"] >= start_day) & (adf["activity_date"] <= end_day)]
        for _, row in adf.iterrows():
            activity_by_day[row["activity_date"]] = row.to_dict()

    rows = []
    sex = profile.get("sex") or ""
    for _, food in daily_food.iterrows():
        d = food["logged_on"]
        act = activity_by_day.get(d, {})
        steps = int(act.get("steps") or 0)
        strength_minutes = float(act.get("strength_minutes") or 0)
        strength_intensity = act.get("strength_intensity") or "Moderado"
        weight_for_day = _weight_on_or_before(measurements, d) or current_weight

        expenditure = daily_expenditure_with_activity(
            weight_kg=weight_for_day,
            height_cm=float(profile["height_cm"]),
            age=int(profile["age"]),
            sex=sex,
            steps=steps,
            strength_minutes=strength_minutes,
            strength_intensity=strength_intensity,
        )

        # Si no se indicó sexo no podemos aplicar Mifflin-St Jeor por sexo.
        # En ese caso usamos el TDEE clásico del perfil como aproximación y no
        # intentamos separar artificialmente gasto base de actividad.
        if expenditure is None:
            fallback = tdee_estimate(
                weight_for_day,
                float(profile["height_cm"]),
                int(profile["age"]),
                sex,
                profile.get("activity_level") or "Sedentario",
            )
            total_exp = float(fallback) if fallback else None
            baseline_kcal = total_exp
            steps_kcal = None
            strength_kcal = None
            activity_extra_kcal = None
        else:
            total_exp = expenditure["total_kcal"]
            baseline_kcal = expenditure["baseline_kcal"]
            steps_kcal = expenditure["steps_kcal"]
            strength_kcal = expenditure["strength_kcal"]
            activity_extra_kcal = steps_kcal + strength_kcal

        calories = float(food["calories_kcal"])
        rows.append({
            "day": d,
            "calories_kcal": calories,
            "protein_g": float(food["protein_g"]),
            "steps": steps,
            "strength_minutes": strength_minutes,
            "strength_intensity": strength_intensity,
            "expenditure_kcal": total_exp,
            "baseline_kcal": baseline_kcal,
            "activity_extra_kcal": activity_extra_kcal,
            "steps_kcal": steps_kcal,
            "strength_kcal": strength_kcal,
            "deficit_kcal": (total_exp - calories) if total_exp is not None else None,
            "activity_logged": d in activity_by_day,
        })

    rdf = pd.DataFrame(rows)
    usable = rdf[rdf["expenditure_kcal"].notna()].copy()
    if usable.empty:
        return {
            "days": rdf,
            "valid_nutrition_days": len(rdf),
            "valid_activity_days": int(rdf["activity_logged"].sum()),
            "projection": None,
        }

    timing = _meal_window_status(profile)
    # Para promedios semanales no tratamos el día actual como terminado mientras
    # aún esté dentro (o antes) del rango habitual de comidas. Así una mañana
    # con pocas calorías no crea un "déficit diario" ficticio.
    completed = usable[usable["day"] < end_day].copy()
    if timing["status"] == "after":
        completed = pd.concat([completed, usable[usable["day"] == end_day]], ignore_index=True)

    basis = completed if not completed.empty else usable.copy()
    avg_intake = float(basis["calories_kcal"].mean())
    avg_exp = float(basis["expenditure_kcal"].mean())
    avg_steps = float(basis["steps"].mean())
    strength_total = float(usable["strength_minutes"].sum())
    avg_protein = float(basis["protein_g"].mean())

    today_rows = usable[usable["day"] == end_day]
    today_consumed = float(today_rows["calories_kcal"].sum()) if not today_rows.empty else 0.0
    today_expenditure = float(today_rows["expenditure_kcal"].iloc[-1]) if not today_rows.empty else None
    today_deficit_so_far = (today_expenditure - today_consumed) if today_expenditure is not None else None

    behavior_projection = behavior_projection_from_energy_balance(
        current_weight_kg=current_weight,
        goal_weight_kg=float(profile["goal_weight_kg"]),
        avg_intake_kcal=avg_intake,
        avg_expenditure_kcal=avg_exp,
        as_of=end_day,
        valid_days=len(basis),
        min_valid_days=4,
    )

    return {
        "days": rdf,
        "valid_nutrition_days": len(rdf),
        "valid_activity_days": int(rdf["activity_logged"].sum()),
        "weekly_balance_days": len(completed),
        "avg_intake_kcal": avg_intake,
        "avg_expenditure_kcal": avg_exp,
        "avg_deficit_kcal_day": avg_exp - avg_intake,
        "avg_steps": avg_steps,
        "strength_minutes_total": strength_total,
        "avg_protein_g": avg_protein,
        "today_consumed_kcal": today_consumed,
        "today_expenditure_kcal": today_expenditure,
        "today_deficit_so_far": today_deficit_so_far,
        "today_complete": timing["status"] == "after",
        "meal_timing": timing,
        "projection": behavior_projection,
    }


def _metric_card(label, value, note=""):
    return (
        "<div class='vj-metric-card'>"
        f"<div class='vj-metric-label'>{html.escape(str(label))}</div>"
        f"<div class='vj-metric-value'>{html.escape(str(value))}</div>"
        f"<div class='vj-metric-note'>{html.escape(str(note))}</div>"
        "</div>"
    )


def _render_weekly_energy_chart(summary, profile):
    """Gráfico diario de gasto base, actividad extra y déficit energético registrado."""
    if not summary:
        return

    days = summary.get("days")
    if days is None or days.empty:
        return

    df = days.copy().sort_values("day")
    if "baseline_kcal" not in df.columns or "deficit_kcal" not in df.columns:
        return

    # El déficit solo se muestra cuando existe nutrición registrada. No asumimos
    # 0 kcal en días sin comidas porque produciría déficits ficticios.
    df["day_label"] = pd.to_datetime(df["day"]).dt.strftime("%d-%m")
    df["activity_extra_kcal"] = pd.to_numeric(df.get("activity_extra_kcal"), errors="coerce").fillna(0.0)
    df["baseline_kcal"] = pd.to_numeric(df.get("baseline_kcal"), errors="coerce")
    df["deficit_kcal"] = pd.to_numeric(df.get("deficit_kcal"), errors="coerce")

    # El objetivo puede variar levemente con el gasto estimado de cada día.
    target_deficits = []
    for _, row in df.iterrows():
        exp = row.get("expenditure_kcal")
        target = _daily_targets(profile, None, exp) if pd.notna(exp) else None
        target_deficits.append(target.get("target_deficit_kcal") if target else None)
    df["target_deficit_kcal"] = target_deficits

    st.markdown("### Balance energético · día a día")
    st.caption(
        "Las barras muestran el gasto base estimado y la actividad extra registrada; "
        "la línea muestra el déficit calórico logrado. El día actual puede ser provisional hasta cerrar tu ventana de comidas."
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["day_label"],
        y=df["baseline_kcal"],
        name="Gasto base",
        marker_color="#6E6E6E",
        hovertemplate="%{x}<br>Gasto base: %{y:.0f} kcal<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["day_label"],
        y=df["activity_extra_kcal"],
        name="Actividad extra",
        marker_color="#9B7BFF",
        hovertemplate="%{x}<br>Actividad extra: %{y:.0f} kcal<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["day_label"],
        y=df["deficit_kcal"],
        name="Déficit logrado",
        mode="lines+markers+text",
        line=dict(color="#111111", width=3),
        marker=dict(color="#111111", size=8),
        text=[f"{v:.0f}" if pd.notna(v) else "" for v in df["deficit_kcal"]],
        textposition="top center",
        hovertemplate="%{x}<br>Déficit: %{y:.0f} kcal<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["day_label"],
        y=df["target_deficit_kcal"],
        name="Déficit objetivo",
        mode="lines",
        line=dict(color="#B0B0B0", width=2, dash="dash"),
        hovertemplate="%{x}<br>Objetivo: %{y:.0f} kcal<extra></extra>",
    ))

    fig.update_layout(
        barmode="stack",
        height=390,
        margin=dict(l=5, r=5, t=20, b=5),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title="kcal",
        xaxis_title="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FAFAFA",
        font=dict(color="#222222"),
        xaxis=dict(gridcolor="#EEEEEE", linecolor="#CFCFCF"),
        yaxis=dict(gridcolor="#E5E5E5", linecolor="#CFCFCF", rangemode="tozero"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Resumen rápido del período para lectura ejecutiva.
    valid = df[df["deficit_kcal"].notna()]
    if not valid.empty:
        avg_def = float(valid["deficit_kcal"].mean())
        avg_extra = float(valid["activity_extra_kcal"].mean())
        total_extra = float(valid["activity_extra_kcal"].sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Déficit medio", f"{avg_def:.0f} kcal/día")
        c2.metric("Actividad extra media", f"{avg_extra:.0f} kcal/día")
        c3.metric("Actividad extra 7 días", f"{total_extra:.0f} kcal")


def behavior_summary_card(sb, uid, profile, measurements):
    summary = _weekly_behavior_summary(sb, uid, profile, measurements, days=7)

    st.markdown("### Nutrición y actividad · últimos 7 días")

    if not summary:
        st.info(
            "Registra comidas y actividad diaria para complementar la proyección "
            "de peso con adherencia nutricional, pasos y entrenamiento de fuerza."
        )
        return

    deficit = summary.get("avg_deficit_kcal_day", 0)
    balance_days = int(summary.get("weekly_balance_days", 0))
    basis_note = f"{balance_days} día(s) cerrado(s)" if balance_days > 0 else "provisional: día actual en curso"
    deficit_note = "solo días ya cerrados" if balance_days > 0 else "provisional; aún no es cierre diario"
    cards = "".join([
        _metric_card("Consumo promedio", f"{summary.get('avg_intake_kcal', 0):.0f} kcal", basis_note),
        _metric_card("Gasto estimado", f"{summary.get('avg_expenditure_kcal', 0):.0f} kcal", "base + actividad registrada"),
        _metric_card("Déficit promedio", f"{deficit:+.0f} kcal/día", deficit_note),
        _metric_card("Pasos promedio", f"{summary.get('avg_steps', 0):,.0f}".replace(",", "."), basis_note),
        _metric_card("Fuerza semanal", f"{summary.get('strength_minutes_total', 0):.0f} min", "minutos acumulados"),
        _metric_card("Proteína promedio", f"{summary.get('avg_protein_g', 0):.0f} g/día", basis_note),
    ])
    st.markdown(f"<div class='vj-metrics-grid'>{cards}</div>", unsafe_allow_html=True)

    st.caption(
        f"Nutrición registrada: {summary.get('valid_nutrition_days', 0)}/7 días · "
        f"Actividad registrada: {summary.get('valid_activity_days', 0)}/7 días. "
        "El día actual no se mezcla con el promedio hasta que termina tu rango habitual de comidas."
    )

    _render_weekly_energy_chart(summary, profile)

    timing = summary.get("meal_timing") or _meal_window_status(profile)
    today_deficit = summary.get("today_deficit_so_far")
    if today_deficit is not None:
        now_txt = timing["now"].strftime("%H:%M")
        window_txt = timing["window_label"]
        fasting_txt = " · ayuno intermitente activo" if timing.get("fasting") else ""

        if timing["status"] == "before":
            st.info(
                f"A las {now_txt}, el balance acumulado de hoy es {today_deficit:+.0f} kcal. "
                f"Tu rango habitual de comidas comienza a las {timing['start'].strftime('%H:%M')} "
                f"({window_txt}){fasting_txt}. No lo interpreto todavía como déficit diario final."
            )
        elif timing["status"] == "within":
            st.info(
                f"A las {now_txt}, llevas un balance acumulado de {today_deficit:+.0f} kcal. "
                f"Aún estás dentro de tu rango de comidas {window_txt}{fasting_txt}, por lo que "
                "este valor es real hasta este momento, pero no representa todavía el déficit final del día."
            )
        else:
            st.caption(
                f"Tu rango habitual de comidas {window_txt} ya terminó. El balance de hoy puede interpretarse "
                "como cierre del día si registraste todas las comidas, bebidas, aceites y porciones."
            )
            if today_deficit > 1200:
                st.warning(
                    "El déficit de hoy está muy por encima de un rango sostenible. Si el registro está completo, "
                    "no conviene intentar repetirlo: mañana vuelve a un déficit moderado y prioriza una comida completa "
                    "con proteína, verduras, una fuente de carbohidratos y grasas saludables. Si faltó registrar algo, "
                    "corrígelo para que la recomendación sea más precisa."
                )

    # Un warning semanal solo se levanta usando días cerrados; nunca por una mañana incompleta.
    if balance_days > 0 and deficit > 1200:
        st.warning(
            "El déficit promedio de los días cerrados es demasiado alto para usarlo como referencia habitual. "
            "Primero confirma que registraste todas las comidas; si está correcto, apunta a un déficit más moderado "
            "y mantenible en el tiempo en lugar de intentar sostener este nivel."
        )

    bp = summary.get("projection")
    if bp and bp.ready:
        pace = bp.theoretical_pace_kg_week or 0
        c1, c2 = st.columns(2)
        c1.metric("Ritmo teórico por hábitos", f"-{pace:.2f} kg/sem" if pace > 0 else "Sin descenso estimable")
        c2.metric(
            "Fecha por hábitos",
            bp.projected_date.strftime("%d-%m-%Y") if bp.projected_date else "Aún no estimable",
        )
        st.caption(
            "Esta es una proyección secundaria de apoyo basada en balance energético estimado. "
            "La fecha principal de Virgils Journey sigue basándose en la tendencia real de peso."
        )
    elif bp:
        st.info(bp.message)


def _prepare_progress_photo(uploaded_file) -> bytes:
    """Valida y re-codifica la foto para reducir tamaño y eliminar EXIF/metadatos."""
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("La foto está vacía.")
    if len(raw) > MAX_PHOTO_BYTES:
        raise ValueError("La foto supera el máximo de 6 MB.")
    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except Exception as exc:
        raise ValueError("El archivo seleccionado no es una imagen válida.") from exc

    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, "white")
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        background.paste(image.convert("RGB"), mask=alpha)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE))
    out = BytesIO()
    # Re-guardar sin EXIF elimina ubicación GPS y otros metadatos del archivo original.
    image.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()


def upload_progress_photo(sb, uid: str, measured_on: date, uploaded_file) -> str:
    photo_bytes = _prepare_progress_photo(uploaded_file)
    path = f"{uid}/{measured_on.isoformat()}/{uuid4().hex}.jpg"
    sb.storage.from_(PHOTO_BUCKET).upload(
        path=path,
        file=photo_bytes,
        file_options={
            "content-type": "image/jpeg",
            "cache-control": "3600",
            "upsert": "false",
        },
    )
    return path


def delete_progress_photo(sb, path: str | None):
    if not path:
        return
    try:
        sb.storage.from_(PHOTO_BUCKET).remove([path])
    except Exception:
        # No bloqueamos una medición por un fallo de limpieza de una foto anterior.
        pass


def signed_photo_url(sb, path: str | None, expires_in: int = 300) -> str | None:
    if not path:
        return None
    try:
        data = sb.storage.from_(PHOTO_BUCKET).create_signed_url(path, expires_in)
        if isinstance(data, dict):
            return data.get("signedURL") or data.get("signedUrl") or data.get("signed_url")
        return getattr(data, "signed_url", None) or getattr(data, "signedURL", None)
    except Exception:
        return None


def progress_photo_gallery(sb, measurements: pd.DataFrame):
    if measurements.empty or "photo_path" not in measurements.columns:
        return
    photos = measurements[measurements["photo_path"].notna()].copy()
    if photos.empty:
        return
    photos = photos.sort_values("measured_on", ascending=False).head(6)
    st.markdown("### Fotos de progreso")
    st.caption("Privadas: se muestran mediante enlaces temporales y se eliminan metadatos EXIF/GPS antes de subirlas.")
    cols = st.columns(2)
    for i, (_, row) in enumerate(photos.iterrows()):
        url = signed_photo_url(sb, row.get("photo_path"))
        if url:
            day_txt = pd.to_datetime(row["measured_on"]).strftime("%d-%m-%Y")
            with cols[i % 2]:
                st.image(url, caption=day_txt, use_container_width=True)


def support_card():
    st.markdown("### Apoya Virgils Journey")
    st.info(
        "Virgils Journey es una aplicación de uso gratuito. "
        "Si deseas realizar un aporte voluntario, puedes solicitar los datos de Cuenta RUT por WhatsApp."
    )
    st.markdown(
        f"[💬 Solicitar datos para aporte voluntario por WhatsApp](https://wa.me/{DONATION_WHATSAPP}?text=Hola%2C%20quisiera%20solicitar%20los%20datos%20para%20realizar%20un%20aporte%20voluntario%20a%20Virgils%20Journey.)"
    )
    st.caption("WhatsApp: +56 9 8582 7304 · Los aportes son completamente voluntarios y no habilitan funciones adicionales.")


def quick_guide(new_user: bool = False, key_prefix: str = "guide", user_name: str = "") -> bool:
    """
    Guía rápida de Virgils Journey.

    Retorna True cuando el usuario termina (o decide saltar) la guía.
    Para usuarios nuevos se muestra antes de crear su perfil; para usuarios
    existentes puede abrirse nuevamente desde Ajustes.
    """
    state_key = f"{key_prefix}_step"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    step = int(st.session_state.get(state_key, 0))
    max_step = 4
    safe_name = html.escape((user_name or "").strip())

    # Progreso visual. La primera pantalla también cuenta como parte de la guía.
    st.progress(min((step + 1) / (max_step + 1), 1.0))
    st.caption(f"Guía rápida · {step + 1} de {max_step + 1}")

    if step == 0:
        st.markdown(
            f"""
            <div class='vj-guide-shell'>
                <div class='vj-guide-kicker'>Antes de comenzar{f", {safe_name}" if safe_name else ""}</div>
                <div class='vj-guide-title'>{f"Este Journey es tuyo, {safe_name}." if safe_name else "Este Journey es tuyo."}</div>
                <div class='vj-quote'>
                    La obsesión siempre vence al talento.<br><br>
                    Obsesiónate con ser tu mejor versión. No busques aprobación externa,
                    hazlo en secreto, y cuando logres tus metas publícalas; no para
                    jactarte, sino para ser la luz que guíe a otros que están en las sombras.
                </div>
                <div class='vj-quote-author'>— Virgilio</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif step == 1:
        st.markdown(
            """
            <div class='vj-guide-shell'>
                <div class='vj-guide-kicker'>1 · Tu punto de partida</div>
                <div class='vj-guide-title'>Mide dónde estás para saber cuánto avanzas.</div>
                <div class='vj-guide-copy'>
                    Comienza registrando peso, medidas corporales, meta y, si quieres,
                    una foto de progreso. Esta primera medición será la referencia de tu Journey.
                </div>
                <div class='vj-guide-step'>
                    <div class='vj-guide-icon'>1</div>
                    <div><div class='vj-guide-step-title'>Haz una medición realista</div>
                    <div class='vj-guide-step-copy'>No necesitas un punto de partida perfecto; necesitas uno verdadero.</div></div>
                </div>
                <div class='vj-guide-step'>
                    <div class='vj-guide-icon'>2</div>
                    <div><div class='vj-guide-step-title'>Define una meta</div>
                    <div class='vj-guide-step-copy'>La app comparará tu tendencia real con el objetivo que definas.</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif step == 2:
        st.markdown(
            """
            <div class='vj-guide-shell'>
                <div class='vj-guide-kicker'>2 · Tu día a día</div>
                <div class='vj-guide-title'>Registra lo que realmente haces.</div>
                <div class='vj-guide-copy'>
                    En <b>Nutrición</b> puedes registrar alimentos, calorías y macronutrientes.
                    También puedes guardar pasos y entrenamiento de fuerza para entender mejor
                    cómo tus hábitos se relacionan con el progreso.
                </div>
                <div class='vj-guide-pills'>
                    <div class='vj-guide-pill'>🥗 Nutrición</div>
                    <div class='vj-guide-pill'>👟 Pasos</div>
                    <div class='vj-guide-pill'>🏋️ Fuerza</div>
                    <div class='vj-guide-pill'>🔥 Balance</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif step == 3:
        st.markdown(
            """
            <div class='vj-guide-shell'>
                <div class='vj-guide-kicker'>3 · Tu progreso</div>
                <div class='vj-guide-title'>Busca tendencias, no días perfectos.</div>
                <div class='vj-guide-copy'>
                    En <b>Inicio</b> verás la evolución de tu peso, medidas y proyecciones.
                    Virgils Journey prioriza la tendencia observada: una semana aislada no define
                    el resultado. Lo importante es acumular consistencia.
                </div>
                <div class='vj-guide-step'>
                    <div class='vj-guide-icon'>↗</div>
                    <div><div class='vj-guide-step-title'>Actualiza tu medición semanal</div>
                    <div class='vj-guide-step-copy'>Con varias mediciones la app puede construir una tendencia más útil.</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            f"""
            <div class='vj-guide-shell'>
                <div class='vj-guide-kicker'>4 · Empieza</div>
                <div class='vj-guide-title'>{f'{safe_name}, no necesitas sentirte preparado. Necesitas comenzar.' if safe_name else 'No necesitas sentirte preparado. Necesitas comenzar.'}</div>
                <div class='vj-guide-copy'>
                    Registra, cumple, revisa y repite. Tu Journey no se construye con un gran día,
                    sino con muchos días suficientemente buenos.
                </div>
                <div class='vj-quote' style='font-size:24px;padding-top:20px;'>Día 1 empieza ahora.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    left, center, right = st.columns([1, 1.35, 1])

    with left:
        if step > 0 and st.button("← Atrás", key=f"{key_prefix}_back", use_container_width=True):
            st.session_state[state_key] = step - 1
            st.rerun()

    with center:
        # En usuarios nuevos permitimos saltar, pero la guía siempre aparece primero.
        if new_user and step < max_step:
            if st.button("Saltar guía", key=f"{key_prefix}_skip", use_container_width=True):
                st.session_state[state_key] = max_step + 1
                st.rerun()

    with right:
        if step < max_step:
            if st.button("Siguiente →", key=f"{key_prefix}_next", use_container_width=True):
                st.session_state[state_key] = step + 1
                st.rerun()
        else:
            label = "Configurar mi punto de partida" if new_user else "Cerrar guía"
            if st.button(label, key=f"{key_prefix}_finish", use_container_width=True):
                st.session_state[state_key] = max_step + 1
                if not new_user:
                    st.session_state["vj_show_quick_guide"] = False
                st.rerun()

    return int(st.session_state.get(state_key, 0)) > max_step


def onboarding(sb, uid, email):
    hero("Tu Journey comienza aquí")

    # Antes de la guía pedimos cómo quiere ser llamado. Se conserva en
    # session_state hasta crear el perfil definitivo en Supabase.
    if not st.session_state.get("vj_identity_ready", False):
        st.markdown("## Antes de comenzar")
        st.caption("Quiero hablarte por tu nombre. Si prefieres, puedes usar un seudónimo dentro de Virgils Journey.")

        google_name = ""
        try:
            google_name = str(getattr(st.user, "name", "") or "").strip()
        except Exception:
            google_name = ""

        email_guess = str(email or "").split("@", 1)[0].replace(".", " ").replace("_", " ").strip().title()
        default_name = st.session_state.get("vj_full_name") or google_name or email_guess

        with st.form("vj_identity_form"):
            full_name = st.text_input("Tu nombre", value=default_name, max_chars=80, placeholder="Ej.: Virgilio Soto")
            display_name = st.text_input(
                "Seudónimo o nombre preferido (opcional)",
                value=st.session_state.get("vj_display_name", ""),
                max_chars=40,
                placeholder="Ej.: Virgil",
                help="Si escribes uno, será el nombre que Virgils Journey usará para hablarte.",
            )
            identity_ok = st.form_submit_button("Continuar a la guía", use_container_width=True)

        if identity_ok:
            clean_full_name = full_name.strip()
            clean_display_name = display_name.strip()
            if not clean_full_name:
                st.warning("Escribe tu nombre para continuar.")
                return
            st.session_state["vj_full_name"] = clean_full_name
            st.session_state["vj_display_name"] = clean_display_name
            st.session_state["vj_identity_ready"] = True
            st.rerun()
        return

    full_name = str(st.session_state.get("vj_full_name") or "").strip()
    display_name = str(st.session_state.get("vj_display_name") or "").strip()
    user_name = display_name or full_name

    # Un usuario sin perfil es un usuario nuevo. La guía se muestra antes de
    # crear su perfil y, una vez completada, pasa a la configuración inicial.
    guide_done = quick_guide(new_user=True, key_prefix="vj_new_user_guide", user_name=user_name)
    if not guide_done:
        return

    st.markdown(f"## Configura tu punto de partida, {html.escape(user_name)}")
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
        st.markdown("#### Horario habitual de comidas")
        intermittent_fasting = st.checkbox(
            "¿Haces ayuno intermitente?",
            value=False,
            help="Virgils Journey usará esta información para no interpretar una mañana en ayuno como un déficit diario final.",
        )
        mc1, mc2 = st.columns(2)
        with mc1:
            eating_window_start = st.time_input("Primera comida habitual", value=dt_time(8, 0), step=900)
        with mc2:
            eating_window_end = st.time_input("Última comida habitual", value=dt_time(21, 0), step=900)
        photo = st.file_uploader("Foto de progreso inicial (opcional)", type=["jpg", "jpeg", "png", "webp"], key="onboarding_photo", help="Máximo 6 MB. La app elimina metadatos EXIF/GPS antes de guardarla.")
        consent = st.checkbox("Entiendo que las proyecciones son estimaciones orientativas y no reemplazan atención médica.")
        submit = st.form_submit_button("Comenzar mi Journey", use_container_width=True)
    if submit:
        if not consent:
            st.warning("Confirma la nota de uso para continuar.")
            return
        sb.table("profiles").insert({
            "user_id": uid, "email": email,
            "full_name": full_name,
            "display_name": display_name or None,
            "age": int(age), "height_cm": float(height),
            "goal_weight_kg": float(goal), "reminder_weekday": WEEKDAYS.index(reminder),
            "sex": None if sex == "No indicar" else sex, "activity_level": activity,
            "timezone": "America/Santiago",
            "intermittent_fasting": bool(intermittent_fasting),
            "eating_window_start": eating_window_start.strftime("%H:%M:%S"),
            "eating_window_end": eating_window_end.strftime("%H:%M:%S")
        }).execute()
        sb.table("measurements").insert({
            "user_id": uid, "measured_on": str(date.today()), "weight_kg": float(weight),
            "chest_cm": float(chest), "waist_cm": float(waist), "neck_cm": float(neck), "hip_cm": float(hip),
            "notes": "Medición inicial"
        }).execute()
        if photo is not None:
            try:
                photo_path = upload_progress_photo(sb, uid, date.today(), photo)
                sb.table("measurements").update({"photo_path": photo_path}).eq("user_id", uid).eq("measured_on", str(date.today())).execute()
            except Exception as exc:
                st.warning(f"La medición se guardó, pero la foto no pudo subirse: {exc}")
        st.success(f"Journey iniciado. Bienvenido, {user_name}.")
        st.rerun()


def weekly_due(df: pd.DataFrame) -> bool:
    if df.empty:
        return True
    last = pd.to_datetime(df["measured_on"]).max().date()
    return (date.today() - last).days >= 7


def dashboard(sb, uid, profile, measurements):
    """Inicio: progreso corporal y tendencia. Nutrición queda concentrada en su propia sección."""
    profile_email = str((profile or {}).get("email") or "")
    email_fallback = profile_email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip().title()
    user_name = preferred_name(profile, email_fallback)
    st.markdown(f"## Hola, {html.escape(user_name)} 👋")
    st.caption("Tu progreso corporal, tendencia y próxima acción en un solo lugar.")

    if measurements.empty:
        st.warning("No hay mediciones. Registra una para comenzar.")
        return

    measurements = measurements.copy()
    measurements["measured_on"] = pd.to_datetime(measurements["measured_on"])
    last = measurements.sort_values("measured_on").iloc[-1]
    last_day = pd.to_datetime(last["measured_on"]).date()
    projection = build_projection(measurements, float(profile["goal_weight_kg"]), float(profile["height_cm"]))

    st.markdown("### Estado del Journey")
    c1, c2, c3 = st.columns(3)
    c1.metric("Peso actual", f"{float(last['weight_kg']):.1f} kg")
    c2.metric("Meta", f"{float(profile['goal_weight_kg']):.1f} kg")
    c3.metric("Progreso", f"{(projection.progress_pct or 0):.0f}%")
    st.progress(min(max((projection.progress_pct or 0) / 100, 0.0), 1.0))
    st.caption(f"Última medición: {last_day.strftime('%d-%m-%Y')}")

    if weekly_due(measurements):
        st.warning("📏 Tu medición semanal está pendiente. Puedes registrarla hoy o completar una fecha anterior si la olvidaste.")
    else:
        st.success("✅ Medición semanal al día.")

    st.markdown("### Tendencia")
    if projection.ready:
        c1, c2 = st.columns(2)
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

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=measurements["measured_on"], y=measurements["weight_kg"],
        mode="lines+markers", name="Peso",
        line=dict(color="#111111", width=3), marker=dict(color="#111111", size=8)
    ))
    fig.add_hline(y=float(profile["goal_weight_kg"]), line_dash="dash", line_color="#777777", annotation_text="Meta")
    fig.update_layout(
        height=320, margin=dict(l=5, r=5, t=25, b=5), legend_orientation="h",
        yaxis_title="kg", xaxis_title="", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FAFAFA", font=dict(color="#222222"),
        xaxis=dict(gridcolor="#E5E5E5", linecolor="#CFCFCF"),
        yaxis=dict(gridcolor="#E5E5E5", linecolor="#CFCFCF"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Últimas medidas corporales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pecho", f"{float(last['chest_cm']):.1f} cm")
    c2.metric("Cintura", f"{float(last['waist_cm']):.1f} cm")
    c3.metric("Cuello", f"{float(last['neck_cm']):.1f} cm")
    c4.metric("Cadera", f"{float(last['hip_cm']):.1f} cm")
    st.caption(f"IMC actual: {projection.bmi_current:.1f} · IMC en meta: {projection.bmi_goal:.1f}" if projection.bmi_current else "")
    progress_photo_gallery(sb, measurements)


def measurement_form(sb, uid, measurements):
    st.markdown("## Nueva medición")
    defaults = {"weight_kg":108.0,"chest_cm":119.0,"waist_cm":112.0,"neck_cm":44.0,"hip_cm":107.0}
    if not measurements.empty:
        row = measurements.sort_values("measured_on").iloc[-1]
        for k in defaults:
            defaults[k] = float(row[k])
    with st.form("measure"):
        day = st.date_input("Fecha de la medición", date.today(), max_value=date.today(), help="Puedes registrar hoy o completar una medición de un día anterior.")
        weight = st.number_input("Peso (kg)", 35.0, 300.0, defaults["weight_kg"], 0.1)
        c1,c2 = st.columns(2)
        with c1:
            chest = st.number_input("Pecho (cm)", 40.0, 220.0, defaults["chest_cm"], 0.5)
            waist = st.number_input("Cintura (cm)", 40.0, 220.0, defaults["waist_cm"], 0.5)
        with c2:
            neck = st.number_input("Cuello (cm)", 20.0, 80.0, defaults["neck_cm"], 0.5)
            hip = st.number_input("Cadera (cm)", 40.0, 220.0, defaults["hip_cm"], 0.5)
        notes = st.text_area("Notas (opcional)", placeholder="Sueño, entrenamiento, viaje, retención de líquidos, etc.")
        photo = st.file_uploader("Foto de progreso (opcional)", type=["jpg", "jpeg", "png", "webp"], key="measurement_photo", help="Máximo 6 MB. Se guarda de forma privada y sin EXIF/GPS.")
        ok = st.form_submit_button("Guardar medición", use_container_width=True)
    if ok:
        previous = sb.table("measurements").select("photo_path").eq("user_id", uid).eq("measured_on", str(day)).limit(1).execute()
        old_photo_path = previous.data[0].get("photo_path") if previous.data else None

        sb.table("measurements").upsert({
            "user_id":uid,"measured_on":str(day),"weight_kg":float(weight),"chest_cm":float(chest),
            "waist_cm":float(waist),"neck_cm":float(neck),"hip_cm":float(hip),"notes":notes
        }, on_conflict="user_id,measured_on").execute()

        if photo is not None:
            try:
                new_photo_path = upload_progress_photo(sb, uid, day, photo)
                sb.table("measurements").update({"photo_path": new_photo_path}).eq("user_id", uid).eq("measured_on", str(day)).execute()
                if old_photo_path and old_photo_path != new_photo_path:
                    delete_progress_photo(sb, old_photo_path)
            except Exception as exc:
                st.warning(f"La medición se guardó, pero la foto no pudo subirse: {exc}")

        st.success("Medición guardada.")
        st.rerun()




def _daily_targets(profile, current_weight, expenditure_kcal):
    """Objetivos orientativos del día, sin requerir nuevas columnas en la base de datos."""
    if not expenditure_kcal:
        return None

    # Déficit moderado y adaptativo: 15% del gasto, acotado entre 350 y 700 kcal/día.
    target_deficit = min(700.0, max(350.0, float(expenditure_kcal) * 0.15))

    sex = str(profile.get("sex") or "").strip().lower()
    floor = 1500.0 if sex == "masculino" else 1200.0 if sex == "femenino" else 1350.0
    calorie_target = max(floor, float(expenditure_kcal) - target_deficit)
    target_deficit = max(0.0, float(expenditure_kcal) - calorie_target)

    goal_weight = float(profile.get("goal_weight_kg") or current_weight or 0)
    reference_weight = goal_weight if goal_weight > 0 else float(current_weight or 0)
    protein_target = max(70.0, reference_weight * 1.6) if reference_weight else 100.0

    return {
        "target_deficit_kcal": target_deficit,
        "calorie_target_kcal": calorie_target,
        "protein_target_g": protein_target,
    }


def _render_progress(label, current, target, unit=""):
    target = max(float(target or 0), 1.0)
    current = max(float(current or 0), 0.0)
    pct = min(100.0, current / target * 100.0)
    st.markdown(
        f"<div class='vj-progress-label'><span>{html.escape(label)}</span>"
        f"<strong>{current:.0f} / {target:.0f} {html.escape(unit)}</strong></div>"
        f"<div class='vj-progress-track'><div class='vj-progress-fill' style='width:{pct:.1f}%'></div></div>",
        unsafe_allow_html=True,
    )


def _daily_coach_context(logs, profile, current_weight, expenditure_kcal, activity_row=None):
    if logs is None or logs.empty or not expenditure_kcal:
        return None

    totals = {
        "consumed_kcal": float(logs["calories_kcal"].fillna(0).sum()),
        "protein_g": float(logs["protein_g"].fillna(0).sum()),
        "carbs_g": float(logs["carbs_g"].fillna(0).sum()),
        "fat_g": float(logs["fat_g"].fillna(0).sum()),
    }
    targets = _daily_targets(profile, current_weight, expenditure_kcal)
    if not targets:
        return None

    act = activity_row or {}
    meals = []
    for _, row in logs.iterrows():
        meals.append({
            "description": str(row.get("description") or "Comida"),
            "calories_kcal": float(row.get("calories_kcal") or 0),
            "protein_g": float(row.get("protein_g") or 0),
            "carbs_g": float(row.get("carbs_g") or 0),
            "fat_g": float(row.get("fat_g") or 0),
        })

    timing = _meal_window_status(profile)
    return {
        **totals,
        **targets,
        "remaining_kcal": targets["calorie_target_kcal"] - totals["consumed_kcal"],
        "remaining_protein_g": max(0.0, targets["protein_target_g"] - totals["protein_g"]),
        "apparent_deficit_so_far": float(expenditure_kcal) - totals["consumed_kcal"],
        "expenditure_kcal": float(expenditure_kcal),
        "steps": int(act.get("steps") or 0),
        "strength_minutes": int(act.get("strength_minutes") or 0),
        "strength_intensity": str(act.get("strength_intensity") or "Moderado"),
        "activity_notes": str(act.get("notes") or ""),
        "current_local_time": timing["now"].strftime("%H:%M"),
        "meal_window_start": timing["start"].strftime("%H:%M"),
        "meal_window_end": timing["end"].strftime("%H:%M"),
        "meal_window_status": timing["status"],
        "meal_window_elapsed_pct": round(timing["elapsed_fraction"] * 100, 1),
        "intermittent_fasting": bool(timing.get("fasting")),
        "meal_schedule_configured": bool(timing.get("configured")),
        "meals": meals,
    }


def _render_ai_daily_coach(context, result=None):
    if not context:
        return

    remaining = float(context.get("remaining_kcal") or 0)
    status = context.get("meal_window_status", "within")
    consumed = float(context.get("consumed_kcal") or 0)
    expenditure = float(context.get("expenditure_kcal") or 0)
    target_deficit = float(context.get("target_deficit_kcal") or 0)
    energy_deficit = expenditure - consumed

    # La tercera tarjeta cambia de significado según si el día sigue abierto o ya cerró.
    if status == "after":
        if remaining >= 0:
            third_title = "Faltaron para objetivo"
            third_value = f"{remaining:.0f} kcal"
        else:
            third_title = "Sobre ingesta objetivo"
            third_value = f"{abs(remaining):.0f} kcal"
    else:
        third_title = "Disponible"
        third_value = f"{remaining:.0f} kcal" if remaining >= 0 else f"{abs(remaining):.0f} kcal sobre objetivo"

    st.markdown("### Balance inteligente de hoy")
    c1, c2, c3 = st.columns(3)
    c1.metric("Objetivo de ingesta", f"{context['calorie_target_kcal']:.0f} kcal")
    c2.metric("Consumido", f"{consumed:.0f} kcal")
    c3.metric(third_title, third_value)

    _render_progress("Calorías", consumed, context["calorie_target_kcal"], "kcal")
    _render_progress("Proteína", context["protein_g"], context["protein_target_g"], "g")

    now_txt = context.get("current_local_time", "")
    start_txt = context.get("meal_window_start", "08:00")
    end_txt = context.get("meal_window_end", "21:00")
    fasting = bool(context.get("intermittent_fasting"))
    fasting_txt = " con ayuno intermitente" if fasting else ""

    if status == "before":
        st.info(
            f"Son las {now_txt}. Tu rango habitual de comidas es {start_txt}–{end_txt}{fasting_txt}. "
            f"El déficit energético acumulado hasta ahora es de aproximadamente {max(0, energy_deficit):.0f} kcal, "
            "pero aún no corresponde evaluarlo como déficit diario final."
        )
    elif status == "within":
        if energy_deficit >= 0:
            balance_txt = f"déficit energético acumulado de aproximadamente {energy_deficit:.0f} kcal"
        else:
            balance_txt = f"superávit energético acumulado de aproximadamente {abs(energy_deficit):.0f} kcal"
        st.info(
            f"Son las {now_txt} y aún estás dentro de tu rango de comidas {start_txt}–{end_txt}{fasting_txt}. "
            f"Tienes un {balance_txt}; todavía puede cambiar con las siguientes comidas del día."
        )
    else:
        if energy_deficit >= 0:
            close_txt = f"déficit calórico estimado de {energy_deficit:.0f} kcal"
        else:
            close_txt = f"superávit calórico estimado de {abs(energy_deficit):.0f} kcal"
        st.caption(
            f"Tu rango habitual de comidas {start_txt}–{end_txt}{fasting_txt} ya terminó. "
            f"Si registraste todo lo consumido, el cierre aproximado de hoy corresponde a un {close_txt}."
        )

    st.caption(
        f"Déficit objetivo orientativo: ~{target_deficit:.0f} kcal/día · "
        "la meta es mantener un déficit sostenible, no maximizarlo."
    )

    if not result:
        return

    warning = result.get("warning") or ""
    body = (
        f"<div class='vj-coach-card'><div class='vj-coach-title'>🤖 {html.escape(result.get('headline') or 'Análisis del día')}</div>"
        f"<div class='vj-coach-text'>{html.escape(result.get('analysis') or '')}</div></div>"
    )
    st.markdown(body, unsafe_allow_html=True)

    action = (result.get("action_message") or "").strip()
    if action:
        st.success(f"🎯 {action}")

    if warning:
        st.warning(warning)

    options = result.get("next_meals") or []
    if options:
        title = "Qué te conviene comer después" if status != "after" else "Opciones equilibradas para tu próxima comida"
        st.markdown(f"**{title}**")
        cols = st.columns(min(3, len(options)))
        for col, meal in zip(cols, options):
            with col:
                st.markdown(f"**{meal.get('name','Opción')}**")
                st.caption(f"≈ {meal.get('kcal',0)} kcal · {meal.get('protein_g',0):.0f} g proteína")
                if meal.get("reason"):
                    st.write(meal["reason"])

    recipe = result.get("tomorrow_lunch") or {}
    if recipe and recipe.get("name"):
        st.markdown("### 🍽️ Almuerzo recomendado para mañana")
        st.markdown(f"**{recipe.get('name')}**")
        if recipe.get("why"):
            st.write(recipe["why"])
        c1, c2 = st.columns(2)
        c1.metric("Calorías aprox.", f"{recipe.get('kcal',0):.0f} kcal")
        c2.metric("Proteína aprox.", f"{recipe.get('protein_g',0):.0f} g")
        ingredients = recipe.get("ingredients") or []
        steps = recipe.get("steps") or []
        if ingredients:
            st.markdown("**Ingredientes**")
            st.markdown("\n".join(f"- {x}" for x in ingredients))
        if steps:
            st.markdown("**Preparación**")
            st.markdown("\n".join(f"{i+1}. {x}" for i, x in enumerate(steps)))

    if result.get("activity_note"):
        st.info(result["activity_note"])
    if result.get("provider"):
        st.caption(f"Análisis generado por {result['provider']}. Las cifras son estimaciones orientativas.")

def _meal_schedule_form(sb, uid, profile, key_prefix="meal_schedule", compact=False):
    schedule = _meal_window(profile)
    if not schedule["configured"]:
        st.info(
            "Para interpretar correctamente tu balance según la hora, indícame si haces ayuno intermitente "
            "y cuál es tu rango habitual de comidas. Se guardará en tu perfil y la IA lo usará desde ahora."
        )

    title = "Horario de alimentación" if compact else "Tu horario de alimentación"
    st.markdown(f"### {title}")
    st.caption(
        "Esto evita que Virgils Journey trate una mañana con pocas calorías como si el día ya hubiera terminado."
    )

    with st.form(f"{key_prefix}_form", clear_on_submit=False):
        fasting = st.checkbox(
            "¿Haces ayuno intermitente?",
            value=bool(schedule["fasting"]),
            help="Solo se usa para interpretar el momento del día y adaptar las sugerencias; no cambia por sí solo tu meta calórica.",
        )
        c1, c2 = st.columns(2)
        with c1:
            start_time = st.time_input(
                "Primera comida habitual",
                value=schedule["start"],
                step=900,
                key=f"{key_prefix}_start",
            )
        with c2:
            end_time = st.time_input(
                "Última comida habitual",
                value=schedule["end"],
                step=900,
                key=f"{key_prefix}_end",
            )
        st.caption(
            "Ejemplo: si comes entre 12:00 y 20:00, antes de las 12:00 la app entenderá que aún estás en ayuno; "
            "a las 16:00 evaluará solo cómo vas hasta ese momento; después de las 20:00 podrá tratar el día como cercano al cierre."
        )
        save_schedule = st.form_submit_button(
            "💾 Guardar horario de alimentación",
            use_container_width=True,
            type="primary" if not schedule["configured"] else "secondary",
        )

    if save_schedule:
        try:
            sb.table("profiles").update({
                "intermittent_fasting": bool(fasting),
                "eating_window_start": start_time.strftime("%H:%M:%S"),
                "eating_window_end": end_time.strftime("%H:%M:%S"),
            }).eq("user_id", uid).execute()
            st.toast("Horario de alimentación guardado.", icon="✅")
            st.rerun()
        except Exception as exc:
            st.error(
                "No fue posible guardar el horario. Ejecuta primero la migración SQL que agrega "
                f"intermittent_fasting, eating_window_start y eating_window_end. Detalle: {exc}"
            )


def nutrition_page(sb, uid, profile, measurements):
    st.markdown("## Nutrición y actividad")
    st.caption("Aquí se concentran alimentación, pasos, fuerza, balance diario y análisis semanal.")

    today = _local_now(profile).date()
    selected_day = st.date_input(
        "Fecha que quieres registrar o revisar",
        value=today,
        max_value=today,
        help="Si olvidaste registrar una comida o entrenamiento, selecciona aquí el día anterior correspondiente.",
        key="nutrition_selected_day",
    )
    is_today = selected_day == today
    day_label = "hoy" if is_today else selected_day.strftime("%d-%m-%Y")
    last_weight = _weight_on_or_before(measurements, selected_day)

    schedule = _meal_window(profile)
    if not schedule["configured"]:
        with st.expander("⚙️ Configurar horario de alimentación", expanded=True):
            _meal_schedule_form(sb, uid, profile, key_prefix="nutrition_meal_schedule", compact=True)
    else:
        fasting_txt = " · ayuno intermitente" if schedule.get("fasting") else ""
        st.caption(
            f"Horario habitual: {schedule['start'].strftime('%H:%M')}–{schedule['end'].strftime('%H:%M')}{fasting_txt}. "
            "Puedes cambiarlo en Ajustes."
        )

    # Datos existentes para el día seleccionado
    day_activity = load_activity(sb, uid, selected_day)
    logs = load_nutrition(sb, uid, selected_day)

    current_steps = 0
    current_strength = 0
    current_intensity = "Moderado"
    current_notes = ""
    if not day_activity.empty:
        arow = day_activity.iloc[-1]
        current_steps = int(arow.get("steps") or 0)
        current_strength = int(arow.get("strength_minutes") or 0)
        current_intensity = arow.get("strength_intensity") or "Moderado"
        current_notes = arow.get("notes") or ""

    intensity_options = ["Suave", "Moderado", "Intenso"]
    if current_intensity not in intensity_options:
        current_intensity = "Moderado"

    # Resumen arriba: primero ver, luego editar/registrar.
    st.markdown(f"### Resumen · {day_label}")
    total_kcal = float(logs["calories_kcal"].fillna(0).sum()) if not logs.empty else 0.0
    total_protein = float(logs["protein_g"].fillna(0).sum()) if not logs.empty else 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calorías", f"{total_kcal:.0f} kcal")
    c2.metric("Proteína", f"{total_protein:.0f} g")
    c3.metric("Pasos", f"{current_steps:,}".replace(",", "."))
    c4.metric("Fuerza", f"{current_strength} min")

    if logs.empty and day_activity.empty:
        st.info(f"Aún no hay registros para {day_label}. Puedes completarlos en las secciones siguientes.")

    tab_food, tab_activity, tab_analysis = st.tabs(["🥗 Comidas", "🏋️ Actividad", "📊 Análisis"])

    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    openrouter_key = st.secrets.get("OPENROUTER_API_KEY", "")
    ai_enabled = bool(gemini_key or openrouter_key)

    with tab_food:
        st.markdown(f"### Registrar comida · {day_label}")
        text = st.text_area(
            "¿Qué comiste?",
            placeholder="Ej.: 200 g de pechuga de pollo, 1 taza de arroz, ensalada y un yogur",
            key=f"food_text_{selected_day}",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Estimar con IA", use_container_width=True, disabled=not ai_enabled, key=f"estimate_food_{selected_day}"):
                if not text.strip():
                    st.warning("Escribe una comida primero.")
                else:
                    try:
                        with st.spinner("Analizando comida..."):
                            est = estimate_nutrition(
                                food_text=text,
                                gemini_api_key=gemini_key,
                                gemini_model=st.secrets.get("GEMINI_MODEL", "gemini-3.6-flash"),
                                openrouter_api_key=openrouter_key,
                                openrouter_model=st.secrets.get("OPENROUTER_MODEL", "openrouter/free"),
                            )
                        st.session_state[f"ai_food_{selected_day}"] = est
                        # IMPORTANTE: los number_input con key propia conservan su valor
                        # en session_state y no adoptan automáticamente el nuevo `value`.
                        # Sincronizamos explícitamente la estimación IA con los campos
                        # visibles para que calorías y macronutrientes se actualicen.
                        st.session_state[f"calories_{selected_day}"] = int(est.get("calories_kcal", 0) or 0)
                        st.session_state[f"protein_{selected_day}"] = float(est.get("protein_g", 0) or 0)
                        st.session_state[f"carbs_{selected_day}"] = float(est.get("carbs_g", 0) or 0)
                        st.session_state[f"fat_{selected_day}"] = float(est.get("fat_g", 0) or 0)
                        st.success("Estimación completada. Valores actualizados.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No fue posible estimar: {e}")
        with c2:
            if ai_enabled:
                providers = []
                if gemini_key:
                    providers.append("Gemini")
                if openrouter_key:
                    providers.append("OpenRouter")
                st.caption("IA disponible · " + " + ".join(providers))
            else:
                st.caption("Configura GEMINI_API_KEY u OPENROUTER_API_KEY para usar IA")

        est = st.session_state.get(f"ai_food_{selected_day}", {})
        with st.form(f"food_{selected_day}"):
            calories = st.number_input("Calorías (kcal)", 0, 10000, int(est.get("calories_kcal", 0) or 0), key=f"calories_{selected_day}")
            protein = st.number_input("Proteína (g)", 0.0, 1000.0, float(est.get("protein_g", 0) or 0), 1.0, key=f"protein_{selected_day}")
            carbs = st.number_input("Carbohidratos (g)", 0.0, 1500.0, float(est.get("carbs_g", 0) or 0), 1.0, key=f"carbs_{selected_day}")
            fat = st.number_input("Grasas (g)", 0.0, 1000.0, float(est.get("fat_g", 0) or 0), 1.0, key=f"fat_{selected_day}")
            if est.get("summary"):
                st.caption(est["summary"])
            if est.get("provider"):
                st.caption(f"Proveedor IA: {est['provider']} · Confianza estimada: {est.get('confidence','media')}")
            save_food = st.form_submit_button(f"Agregar comida a {day_label}", use_container_width=True)

        if save_food:
            sb.table("nutrition_logs").insert({
                "user_id": uid,
                "logged_on": str(selected_day),
                "description": text or "Registro manual",
                "calories_kcal": int(calories),
                "protein_g": float(protein),
                "carbs_g": float(carbs),
                "fat_g": float(fat),
                "ai_estimated": bool(est),
            }).execute()
            st.session_state.pop(f"ai_food_{selected_day}", None)
            # Limpiar el formulario para que la siguiente comida no reutilice
            # calorías/macros de la comida recién guardada.
            for _key in (
                f"calories_{selected_day}",
                f"protein_{selected_day}",
                f"carbs_{selected_day}",
                f"fat_{selected_day}",
                f"food_text_{selected_day}",
            ):
                st.session_state.pop(_key, None)
            if is_today:
                st.session_state["refresh_daily_coach"] = True
            st.toast(f"Comida guardada en {day_label}.", icon="✅")
            st.rerun()

        logs = load_nutrition(sb, uid, selected_day)
        if not logs.empty:
            st.markdown("#### Comidas registradas")
            st.dataframe(
                logs[["description", "calories_kcal", "protein_g", "carbs_g", "fat_g"]],
                use_container_width=True,
                hide_index=True,
            )

    with tab_activity:
        st.markdown(f"### Actividad · {day_label}")
        with st.form(f"daily_activity_form_{selected_day}"):
            c1, c2 = st.columns(2)
            with c1:
                steps = st.number_input("Pasos del día", 0, 100000, current_steps, 500, key=f"steps_{selected_day}")
            with c2:
                strength_minutes = st.number_input("Entrenamiento de fuerza (min)", 0, 600, current_strength, 5, key=f"strength_{selected_day}")
            strength_intensity = st.selectbox(
                "Intensidad de fuerza", intensity_options,
                index=intensity_options.index(current_intensity),
                help="Se usa para estimar gasto; no califica la calidad del entrenamiento.",
                key=f"intensity_{selected_day}",
            )
            activity_notes = st.text_input(
                "Notas de actividad (opcional)", value=current_notes,
                placeholder="Ej.: piernas, torso, caminata larga, etc.",
                key=f"activity_notes_{selected_day}",
            )
            save_activity = st.form_submit_button(f"Guardar actividad de {day_label}", use_container_width=True)

        if save_activity:
            sb.table("daily_activity").upsert({
                "user_id": uid,
                "activity_date": str(selected_day),
                "steps": int(steps),
                "strength_minutes": int(strength_minutes),
                "strength_intensity": strength_intensity,
                "notes": activity_notes,
            }, on_conflict="user_id,activity_date").execute()
            if is_today:
                st.session_state["refresh_daily_coach"] = True
            st.toast(f"Actividad guardada en {day_label}.", icon="✅")
            st.rerun()

        if last_weight:
            activity_estimate = daily_expenditure_with_activity(
                weight_kg=last_weight,
                height_cm=float(profile["height_cm"]),
                age=int(profile["age"]),
                sex=profile.get("sex") or "",
                steps=current_steps,
                strength_minutes=current_strength,
                strength_intensity=current_intensity,
            )
            if activity_estimate:
                c1, c2, c3 = st.columns(3)
                c1.metric("Gasto base", f"{activity_estimate['baseline_kcal']:.0f} kcal")
                c2.metric("Actividad extra", f"{activity_estimate['steps_kcal'] + activity_estimate['strength_kcal']:.0f} kcal")
                c3.metric("Gasto total", f"{activity_estimate['total_kcal']:.0f} kcal")

    with tab_analysis:
        logs = load_nutrition(sb, uid, selected_day)
        day_activity = load_activity(sb, uid, selected_day)
        activity_row = day_activity.iloc[-1].to_dict() if not day_activity.empty else {}

        if logs.empty:
            st.info("Registra al menos una comida para calcular el balance nutricional de este día.")
        else:
            exp_day = None
            if last_weight:
                exp_detail = daily_expenditure_with_activity(
                    weight_kg=last_weight,
                    height_cm=float(profile["height_cm"]),
                    age=int(profile["age"]),
                    sex=profile.get("sex") or "",
                    steps=int(activity_row.get("steps") or 0),
                    strength_minutes=int(activity_row.get("strength_minutes") or 0),
                    strength_intensity=activity_row.get("strength_intensity") or "Moderado",
                )
                exp_day = float(exp_detail["total_kcal"]) if exp_detail else tdee_estimate(
                    last_weight, float(profile["height_cm"]), int(profile["age"]),
                    profile.get("sex") or "", profile.get("activity_level") or "Sedentario"
                )

            coach_context = _daily_coach_context(logs, profile, last_weight, exp_day, activity_row=activity_row)
            if coach_context and not is_today:
                # Un día pasado se analiza como día cerrado; no usamos la hora actual para juzgarlo.
                coach_context["meal_window_status"] = "after"
                coach_context["meal_window_elapsed_pct"] = 100.0
                coach_context["current_local_time"] = "23:59"

            coach_key = f"daily_coach_result_{selected_day}"
            coach_result = st.session_state.get(coach_key)
            auto_refresh = is_today and bool(st.session_state.pop("refresh_daily_coach", False))
            analyze_now = auto_refresh
            if ai_enabled and coach_context and not auto_refresh:
                button_label = "🤖 Actualizar análisis de hoy y menú de mañana" if is_today else "🤖 Analizar este día"
                if st.button(button_label, use_container_width=True, key=f"analyze_{selected_day}"):
                    analyze_now = True

            if analyze_now and ai_enabled and coach_context:
                try:
                    with st.spinner("Analizando comidas, actividad y balance..."):
                        coach_result = analyze_daily_balance(
                            context=coach_context,
                            gemini_api_key=gemini_key,
                            gemini_model=st.secrets.get("GEMINI_MODEL", "gemini-3.6-flash"),
                            openrouter_api_key=openrouter_key,
                            openrouter_model=st.secrets.get("OPENROUTER_MODEL", "openrouter/free"),
                        )
                    st.session_state[coach_key] = coach_result
                except Exception as exc:
                    st.warning(f"No fue posible generar el análisis IA: {exc}")

            _render_ai_daily_coach(coach_context, coach_result)

        st.divider()
        behavior_summary_card(sb, uid, profile, measurements)
        st.caption(
            "El resumen de 7 días vive aquí para evitar duplicar información con Inicio. "
            "La proyección principal de peso sigue basándose en tus mediciones reales."
        )


def settings_page(sb, uid, profile):
    st.markdown("## Ajustes")

    # Siempre recargar el perfil desde Supabase para mostrar los datos más recientes.
    fresh_profile = get_profile(sb, uid) or profile or {}

    # ------------------------------------------------------------------
    # GUÍA RÁPIDA
    # ------------------------------------------------------------------
    st.markdown("### Guía rápida")
    st.caption("Puedes volver a ver el recorrido inicial cuando quieras.")
    if st.button("Ver guía rápida", key="open_quick_guide", use_container_width=True):
        st.session_state["vj_show_quick_guide"] = True
        st.session_state["vj_replay_guide_step"] = 0
        st.rerun()

    current_preferred_name = preferred_name(fresh_profile)

    if st.session_state.get("vj_show_quick_guide", False):
        quick_guide(
            new_user=False,
            key_prefix="vj_replay_guide",
            user_name=current_preferred_name,
        )
        st.divider()

    # ------------------------------------------------------------------
    # IDENTIDAD - FORMULARIO INDEPENDIENTE
    # ------------------------------------------------------------------
    st.markdown("### Tu identidad en Virgils Journey")
    st.caption(
        "Puedes cambiar tu nombre o elegir un seudónimo. "
        "El seudónimo tendrá prioridad en los saludos de la aplicación."
    )

    with st.form("identity_settings_form", clear_on_submit=False):
        full_name = st.text_input(
            "Tu nombre",
            value=str(fresh_profile.get("full_name") or ""),
            max_chars=80,
            placeholder="Ej.: Virgilio Soto",
        )
        display_name = st.text_input(
            "Seudónimo o nombre preferido (opcional)",
            value=str(fresh_profile.get("display_name") or ""),
            max_chars=40,
            placeholder="Ej.: Virgil",
            help="Si escribes uno, Virgils Journey usará este nombre para hablarte.",
        )
        save_identity = st.form_submit_button(
            "💾 Guardar nombre y seudónimo",
            use_container_width=True,
            type="primary",
        )

    if save_identity:
        clean_full_name = str(full_name or "").strip()
        clean_display_name = str(display_name or "").strip()

        if not clean_full_name:
            st.error("Debes ingresar tu nombre antes de guardar.")
        else:
            try:
                sb.table("profiles").update({
                    "full_name": clean_full_name,
                    "display_name": clean_display_name or None,
                }).eq("user_id", uid).execute()

                # Actualizar también la sesión para que el cambio se refleje inmediatamente.
                st.session_state["vj_full_name"] = clean_full_name
                st.session_state["vj_display_name"] = clean_display_name
                st.session_state["vj_preferred_name"] = clean_display_name or clean_full_name

                # Verificar que Supabase realmente haya persistido los valores.
                updated_profile = get_profile(sb, uid)
                if not updated_profile:
                    st.error("No pude verificar el perfil después de guardar.")
                else:
                    saved_full_name = str(updated_profile.get("full_name") or "").strip()
                    saved_display_name = str(updated_profile.get("display_name") or "").strip()

                    if saved_full_name != clean_full_name or saved_display_name != clean_display_name:
                        st.error(
                            "Supabase no devolvió los nuevos datos. Revisa que las columnas "
                            "full_name y display_name existan y que la política RLS permita UPDATE."
                        )
                    else:
                        st.toast(
                            f"Guardado. Desde ahora te llamaré {saved_display_name or saved_full_name}.",
                            icon="✅",
                        )
                        st.rerun()
            except Exception as e:
                st.error(f"No fue posible guardar el nombre o seudónimo: {e}")

    st.divider()

    # ------------------------------------------------------------------
    # PREFERENCIAS - FORMULARIO INDEPENDIENTE
    # ------------------------------------------------------------------
    st.markdown("### Preferencias")

    with st.form("settings_preferences_form", clear_on_submit=False):
        goal = st.number_input(
            "Meta de peso (kg)",
            35.0,
            300.0,
            float(fresh_profile.get("goal_weight_kg") or 80.0),
            0.1,
        )

        reminder_index = int(fresh_profile.get("reminder_weekday") or 0)
        if reminder_index < 0 or reminder_index >= len(WEEKDAYS):
            reminder_index = 0

        reminder = st.selectbox(
            "Día de recordatorio",
            WEEKDAYS,
            index=reminder_index,
        )

        activity_options = ["Sedentario", "Ligero", "Moderado", "Alto", "Muy alto"]
        current_activity = fresh_profile.get("activity_level") or "Sedentario"
        if current_activity not in activity_options:
            current_activity = "Sedentario"

        activity = st.selectbox(
            "Actividad",
            activity_options,
            index=activity_options.index(current_activity),
        )

        save_preferences = st.form_submit_button(
            "💾 Guardar preferencias",
            use_container_width=True,
        )

    if save_preferences:
        try:
            sb.table("profiles").update({
                "goal_weight_kg": float(goal),
                "reminder_weekday": WEEKDAYS.index(reminder),
                "activity_level": activity,
            }).eq("user_id", uid).execute()

            st.toast("Preferencias guardadas.", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(f"No fue posible guardar las preferencias: {e}")

    st.divider()
    _meal_schedule_form(sb, uid, fresh_profile, key_prefix="settings_meal_schedule", compact=False)

    # ------------------------------------------------------------------
    # INFORMACIÓN
    # ------------------------------------------------------------------
    st.markdown("### Metodología")
    st.write(
        "La proyección se activa con al menos 4 mediciones distribuidas en ~4 semanas. "
        "Usa una tendencia robusta de peso (mediana de pendientes entre pares de puntos), "
        "y se actualiza con hasta las últimas 8 mediciones."
    )
    st.write(
        "El rango de 1–2 lb/semana se muestra solo como referencia de pérdida gradual citada por CDC. "
        "La fecha objetivo es una estimación y puede cambiar por líquidos, adherencia, enfermedad, "
        "medicamentos, sueño y otros factores."
    )
    st.write(
        "La proyección por hábitos es secundaria: utiliza calorías registradas, pasos y minutos de fuerza "
        "para estimar el balance energético. El peso observado sigue siendo la referencia principal porque "
        "el gasto y la ingesta tienen error de estimación."
    )

    st.markdown("### Privacidad")
    st.caption(
        "Las mediciones y fotos se asocian a tu usuario. Las fotos se guardan en un bucket privado "
        "de Supabase y se muestran con enlaces temporales. Evita subir imágenes que no quieras "
        "conservar en el servicio."
    )

    support_card()

    if st.button("Cerrar sesión", use_container_width=True):
        was_google = st.session_state.get("auth_provider") == "google"
        sign_out()
        if was_google:
            st.logout()
        else:
            st.rerun()


# --- app ---
# Inicializar estado de sesión para evitar KeyError en reruns parciales
for key in ["access_token", "refresh_token", "user_id", "email", "auth_provider"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "vj_show_quick_guide" not in st.session_state:
    st.session_state["vj_show_quick_guide"] = False

if not st.session_state.get("access_token") or not st.session_state.get("user_id"):
    if sync_google_session_to_supabase():
        st.rerun()
    auth_screen()

sb = client()
uid = st.session_state.get("user_id")
email = st.session_state.get("email", "")

if not uid:
    st.session_state["access_token"] = None
    st.session_state["refresh_token"] = None
    auth_screen()

profile = get_profile(sb, uid)
if not profile:
    onboarding(sb, uid, email)
    st.stop()

measurements = load_measurements(sb, uid)

# Encabezado global + navegación visible en formato móvil
user_name = preferred_name(profile, str(email or "").split("@", 1)[0])
hero(f"Hola, {html.escape(user_name)} · tu viaje, medido con datos y consistencia")

tab_inicio, tab_medicion, tab_nutricion, tab_ajustes = st.tabs([
    "🏠 Inicio",
    "📏 Medición",
    "🥗 Nutrición",
    "⚙️ Ajustes",
])

with tab_inicio:
    dashboard(sb, uid, profile, measurements)

with tab_medicion:
    measurement_form(sb, uid, measurements)

with tab_nutricion:
    nutrition_page(sb, uid, profile, measurements)

with tab_ajustes:
    settings_page(sb, uid, profile)
