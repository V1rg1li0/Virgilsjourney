
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

from datetime import date, datetime, timedelta
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
from ai_nutrition import estimate_nutrition

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


def _weekly_behavior_summary(sb, uid, profile, measurements, days=7):
    """
    Resume nutrición + pasos + fuerza para los últimos N días.
    No interpreta la ausencia de comida como 0 kcal: solo usa días con
    al menos un registro nutricional.
    """
    all_nutrition = load_nutrition(sb, uid)
    all_activity = load_activity(sb, uid)

    end_day = date.today()
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

        expenditure = daily_expenditure_with_activity(
            weight_kg=current_weight,
            height_cm=float(profile["height_cm"]),
            age=int(profile["age"]),
            sex=sex,
            steps=steps,
            strength_minutes=strength_minutes,
            strength_intensity=strength_intensity,
        )

        # Si no se indicó sexo no podemos aplicar Mifflin-St Jeor por sexo.
        # En ese caso usamos el TDEE clásico del perfil como aproximación.
        if expenditure is None:
            fallback = tdee_estimate(
                current_weight,
                float(profile["height_cm"]),
                int(profile["age"]),
                sex,
                profile.get("activity_level") or "Sedentario",
            )
            total_exp = float(fallback) if fallback else None
            steps_kcal = None
            strength_kcal = None
        else:
            total_exp = expenditure["total_kcal"]
            steps_kcal = expenditure["steps_kcal"]
            strength_kcal = expenditure["strength_kcal"]

        rows.append({
            "day": d,
            "calories_kcal": float(food["calories_kcal"]),
            "protein_g": float(food["protein_g"]),
            "steps": steps,
            "strength_minutes": strength_minutes,
            "strength_intensity": strength_intensity,
            "expenditure_kcal": total_exp,
            "steps_kcal": steps_kcal,
            "strength_kcal": strength_kcal,
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

    avg_intake = float(usable["calories_kcal"].mean())
    avg_exp = float(usable["expenditure_kcal"].mean())
    avg_steps = float(usable["steps"].mean())
    strength_total = float(usable["strength_minutes"].sum())
    avg_protein = float(usable["protein_g"].mean())

    behavior_projection = behavior_projection_from_energy_balance(
        current_weight_kg=current_weight,
        goal_weight_kg=float(profile["goal_weight_kg"]),
        avg_intake_kcal=avg_intake,
        avg_expenditure_kcal=avg_exp,
        as_of=end_day,
        valid_days=len(usable),
        min_valid_days=4,
    )

    return {
        "days": rdf,
        "valid_nutrition_days": len(rdf),
        "valid_activity_days": int(rdf["activity_logged"].sum()),
        "avg_intake_kcal": avg_intake,
        "avg_expenditure_kcal": avg_exp,
        "avg_deficit_kcal_day": avg_exp - avg_intake,
        "avg_steps": avg_steps,
        "strength_minutes_total": strength_total,
        "avg_protein_g": avg_protein,
        "projection": behavior_projection,
    }


def behavior_summary_card(sb, uid, profile, measurements):
    summary = _weekly_behavior_summary(sb, uid, profile, measurements, days=7)

    st.markdown("### Nutrición y actividad · últimos 7 días")

    if not summary:
        st.info(
            "Registra comidas y actividad diaria para complementar la proyección "
            "de peso con adherencia nutricional, pasos y entrenamiento de fuerza."
        )
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Consumo promedio", f"{summary.get('avg_intake_kcal', 0):.0f} kcal")
    c2.metric("Gasto estimado", f"{summary.get('avg_expenditure_kcal', 0):.0f} kcal")
    c3.metric("Balance promedio", f"{summary.get('avg_deficit_kcal_day', 0):+.0f} kcal/día")

    c1, c2, c3 = st.columns(3)
    c1.metric("Pasos promedio", f"{summary.get('avg_steps', 0):,.0f}".replace(",", "."))
    c2.metric("Fuerza semanal", f"{summary.get('strength_minutes_total', 0):.0f} min")
    c3.metric("Proteína promedio", f"{summary.get('avg_protein_g', 0):.0f} g/día")

    st.caption(
        f"Nutrición registrada: {summary.get('valid_nutrition_days', 0)}/7 días · "
        f"Actividad registrada: {summary.get('valid_activity_days', 0)}/7 días."
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
            "timezone": "America/Santiago"
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
    profile_email = str((profile or {}).get("email") or "")
    email_fallback = profile_email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip().title()
    user_name = preferred_name(profile, email_fallback)
    st.markdown(f"## Hola, {html.escape(user_name)} 👋")
    st.caption("Este es tu Journey de hoy.")

    if measurements.empty:
        st.warning("No hay mediciones. Registra una para comenzar.")
        support_card()
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
    fig.add_trace(go.Scatter(x=measurements["measured_on"], y=measurements["weight_kg"], mode="lines+markers", name="Peso", line=dict(color="#111111", width=3), marker=dict(color="#111111", size=8)))
    fig.add_hline(y=float(profile["goal_weight_kg"]), line_dash="dash", line_color="#777777", annotation_text="Meta")
    fig.update_layout(
        height=320,
        margin=dict(l=5,r=5,t=25,b=5),
        legend_orientation="h",
        yaxis_title="kg",
        xaxis_title="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FAFAFA",
        font=dict(color="#222222"),
        xaxis=dict(gridcolor="#E5E5E5", linecolor="#CFCFCF"),
        yaxis=dict(gridcolor="#E5E5E5", linecolor="#CFCFCF"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    behavior_summary_card(sb, uid, profile, measurements)

    st.markdown("### Medidas corporales")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Pecho", f"{float(last['chest_cm']):.1f} cm")
    c2.metric("Cintura", f"{float(last['waist_cm']):.1f} cm")
    c3.metric("Cuello", f"{float(last['neck_cm']):.1f} cm")
    c4.metric("Cadera", f"{float(last['hip_cm']):.1f} cm")
    st.caption(f"IMC actual: {projection.bmi_current:.1f} · IMC en meta: {projection.bmi_goal:.1f}" if projection.bmi_current else "")
    support_card()
    progress_photo_gallery(sb, measurements)


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

    support_card()


def nutrition_page(sb, uid, profile, measurements):
    st.markdown("## Nutrición y actividad")
    st.caption(
        "Registra lo que comiste y tu actividad del día. La IA, el gasto energético "
        "y las proyecciones son estimaciones orientativas."
    )

    today = date.today()
    last_weight = _latest_weight(measurements)

    # --------------------------
    # Actividad del día
    # --------------------------
    st.markdown("### Actividad de hoy")
    today_activity = load_activity(sb, uid, today)

    current_steps = 0
    current_strength = 0
    current_intensity = "Moderado"
    current_notes = ""

    if not today_activity.empty:
        arow = today_activity.iloc[-1]
        current_steps = int(arow.get("steps") or 0)
        current_strength = int(arow.get("strength_minutes") or 0)
        current_intensity = arow.get("strength_intensity") or "Moderado"
        current_notes = arow.get("notes") or ""

    intensity_options = ["Suave", "Moderado", "Intenso"]
    if current_intensity not in intensity_options:
        current_intensity = "Moderado"

    with st.form("daily_activity_form"):
        c1, c2 = st.columns(2)
        with c1:
            steps = st.number_input(
                "Pasos del día",
                min_value=0,
                max_value=100000,
                value=current_steps,
                step=500,
            )
        with c2:
            strength_minutes = st.number_input(
                "Entrenamiento de fuerza (min)",
                min_value=0,
                max_value=600,
                value=current_strength,
                step=5,
            )

        strength_intensity = st.selectbox(
            "Intensidad de fuerza",
            intensity_options,
            index=intensity_options.index(current_intensity),
            help="Suave, moderado o intenso. Se usa para estimar gasto, no para calificar el entrenamiento.",
        )
        activity_notes = st.text_input(
            "Notas de actividad (opcional)",
            value=current_notes,
            placeholder="Ej.: piernas, torso, caminata larga, etc.",
        )
        save_activity = st.form_submit_button("Guardar actividad de hoy", use_container_width=True)

    if save_activity:
        sb.table("daily_activity").upsert(
            {
                "user_id": uid,
                "activity_date": str(today),
                "steps": int(steps),
                "strength_minutes": int(strength_minutes),
                "strength_intensity": strength_intensity,
                "notes": activity_notes,
            },
            on_conflict="user_id,activity_date",
        ).execute()
        st.success("Actividad del día guardada.")
        st.rerun()

    # Gasto del día con pasos + fuerza explícitos
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
            c2.metric(
                "Actividad extra",
                f"{activity_estimate['steps_kcal'] + activity_estimate['strength_kcal']:.0f} kcal",
            )
            c3.metric("Gasto total estimado", f"{activity_estimate['total_kcal']:.0f} kcal")
            st.caption(
                f"Pasos ≈ {activity_estimate['steps_kcal']:.0f} kcal extra · "
                f"Fuerza ≈ {activity_estimate['strength_kcal']:.0f} kcal extra. "
                "Se usa una base sedentaria para reducir doble conteo."
            )
        else:
            fallback_tdee = tdee_estimate(
                last_weight,
                float(profile["height_cm"]),
                int(profile["age"]),
                profile.get("sex") or "",
                profile.get("activity_level") or "Sedentario",
            )
            if fallback_tdee:
                st.info(
                    f"Gasto diario estimado por perfil: **{fallback_tdee:.0f} kcal/día**. "
                    "Para usar pasos y fuerza en el cálculo más detallado, indica sexo en el perfil."
                )

    # --------------------------
    # Registro de comida
    # --------------------------
    st.markdown("### Registrar comida")
    text = st.text_area(
        "¿Qué comiste?",
        placeholder="Ej.: 200 g de pechuga de pollo, 1 taza de arroz, ensalada y un yogur",
    )

    gemini_key = st.secrets.get("GEMINI_API_KEY", "")
    openrouter_key = st.secrets.get("OPENROUTER_API_KEY", "")
    ai_enabled = bool(gemini_key or openrouter_key)

    c1,c2 = st.columns(2)
    with c1:
        if st.button("Estimar con IA", use_container_width=True, disabled=not ai_enabled):
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
                    st.session_state.ai_food = est
                    st.success("Estimación completada.")
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

    est = st.session_state.get("ai_food", {})
    with st.form("food"):
        calories = st.number_input("Calorías (kcal)", 0, 10000, int(est.get("calories_kcal",0) or 0))
        protein = st.number_input("Proteína (g)", 0.0, 1000.0, float(est.get("protein_g",0) or 0), 1.0)
        carbs = st.number_input("Carbohidratos (g)", 0.0, 1500.0, float(est.get("carbs_g",0) or 0), 1.0)
        fat = st.number_input("Grasas (g)", 0.0, 1000.0, float(est.get("fat_g",0) or 0), 1.0)
        if est.get("summary"):
            st.caption(est["summary"])
        if est.get("provider"):
            st.caption(
                f"Proveedor IA: {est['provider']} · "
                f"Confianza estimada: {est.get('confidence','media')}"
            )
        save_food = st.form_submit_button("Agregar al día", use_container_width=True)

    if save_food:
        sb.table("nutrition_logs").insert(
            {
                "user_id": uid,
                "logged_on": str(today),
                "description": text or "Registro manual",
                "calories_kcal": int(calories),
                "protein_g": float(protein),
                "carbs_g": float(carbs),
                "fat_g": float(fat),
                "ai_estimated": bool(est),
            }
        ).execute()
        st.session_state.pop("ai_food", None)
        st.rerun()

    logs = load_nutrition(sb, uid, today)
    if not logs.empty:
        st.markdown("### Resumen de hoy")
        c1,c2,c3 = st.columns(3)
        total_kcal = float(logs["calories_kcal"].fillna(0).sum())
        total_protein = float(logs["protein_g"].fillna(0).sum())
        c1.metric("Calorías", f"{total_kcal:.0f} kcal")
        c2.metric("Proteína", f"{total_protein:.0f} g")

        today_activity = load_activity(sb, uid, today)
        steps_today = int(today_activity.iloc[-1]["steps"]) if not today_activity.empty else 0
        c3.metric("Pasos", f"{steps_today:,}".replace(",", "."))

        st.dataframe(
            logs[["description","calories_kcal","protein_g","carbs_g","fat_g"]],
            use_container_width=True,
            hide_index=True,
        )

    behavior_summary_card(sb, uid, profile, measurements)

    st.caption(
        "La proyección por hábitos usa los días con nutrición registrada y estima el gasto "
        "a partir de Mifflin–St Jeor, una base sedentaria y la actividad explícita. "
        "No sustituye la tendencia real de peso."
    )

    support_card()

def settings_page(sb, uid, profile):
    st.markdown("## Ajustes")

    st.markdown("### Guía rápida")
    st.caption("Puedes volver a ver el recorrido inicial cuando quieras.")
    if st.button("Ver guía rápida", key="open_quick_guide", use_container_width=True):
        st.session_state["vj_show_quick_guide"] = True
        st.session_state["vj_replay_guide_step"] = 0
        st.rerun()

    current_preferred_name = preferred_name(profile)

    if st.session_state.get("vj_show_quick_guide", False):
        quick_guide(new_user=False, key_prefix="vj_replay_guide", user_name=current_preferred_name)
        st.divider()

    with st.form("settings"):
        st.markdown("### Tu identidad en Virgils Journey")
        full_name = st.text_input("Tu nombre", value=str(profile.get("full_name") or ""), max_chars=80)
        display_name = st.text_input(
            "Seudónimo o nombre preferido (opcional)",
            value=str(profile.get("display_name") or ""),
            max_chars=40,
            help="Si lo dejas vacío, Virgils Journey usará tu nombre.",
        )
        goal = st.number_input("Meta de peso (kg)", 35.0, 300.0, float(profile["goal_weight_kg"]), 0.1)
        reminder = st.selectbox("Día de recordatorio", WEEKDAYS, index=int(profile.get("reminder_weekday") or 0))
        activity = st.selectbox("Actividad", ["Sedentario","Ligero","Moderado","Alto","Muy alto"], index=["Sedentario","Ligero","Moderado","Alto","Muy alto"].index(profile.get("activity_level") or "Sedentario"))
        ok = st.form_submit_button("Guardar")
    if ok:
        clean_full_name = full_name.strip()
        clean_display_name = display_name.strip()
        if not clean_full_name:
            st.warning("El nombre no puede quedar vacío.")
        else:
            sb.table("profiles").update({
                "full_name": clean_full_name,
                "display_name": clean_display_name or None,
                "goal_weight_kg": float(goal),
                "reminder_weekday": WEEKDAYS.index(reminder),
                "activity_level": activity,
            }).eq("user_id",uid).execute()
            st.success(f"Ajustes guardados. Te llamaré {clean_display_name or clean_full_name}.")
            st.rerun()
    st.markdown("### Metodología")
    st.write("La proyección se activa con al menos 4 mediciones distribuidas en ~4 semanas. Usa una tendencia robusta de peso (mediana de pendientes entre pares de puntos), y se actualiza con hasta las últimas 8 mediciones.")
    st.write("El rango de 1–2 lb/semana se muestra solo como referencia de pérdida gradual citada por CDC. La fecha objetivo es una estimación y puede cambiar por líquidos, adherencia, enfermedad, medicamentos, sueño y otros factores.")
    st.write("La proyección por hábitos es secundaria: utiliza calorías registradas, pasos y minutos de fuerza para estimar el balance energético. El peso observado sigue siendo la referencia principal porque el gasto y la ingesta tienen error de estimación.")

    st.markdown("### Privacidad")
    st.caption("Las mediciones y fotos se asocian a tu usuario. Las fotos se guardan en un bucket privado de Supabase y se muestran con enlaces temporales. Evita subir imágenes que no quieras conservar en el servicio.")

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
