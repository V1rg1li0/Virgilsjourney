from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional
import math
import numpy as np
import pandas as pd

@dataclass
class Projection:
    ready: bool
    message: str
    pace_kg_week: Optional[float] = None
    projected_date: Optional[date] = None
    weeks_to_goal: Optional[float] = None
    progress_pct: Optional[float] = None
    bmi_current: Optional[float] = None
    bmi_goal: Optional[float] = None
    first_four_pace_kg_week: Optional[float] = None


def bmi(weight_kg: float, height_cm: float) -> float:
    h = height_cm / 100.0
    return weight_kg / (h * h) if h > 0 else float("nan")


def _theil_sen_slope_per_day(df: pd.DataFrame) -> Optional[float]:
    if len(df) < 2:
        return None
    d0 = pd.to_datetime(df["measured_on"]).min()
    x = (pd.to_datetime(df["measured_on"]) - d0).dt.days.to_numpy(dtype=float)
    y = df["weight_kg"].to_numpy(dtype=float)
    slopes = []
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx = x[j] - x[i]
            if dx > 0:
                slopes.append((y[j] - y[i]) / dx)
    if not slopes:
        return None
    return float(np.median(slopes))


def build_projection(
    measurements: pd.DataFrame,
    goal_weight_kg: float,
    height_cm: float,
) -> Projection:
    if measurements is None or measurements.empty:
        return Projection(False, "Registra tu primera medición para comenzar.")

    df = measurements.copy()
    df["measured_on"] = pd.to_datetime(df["measured_on"]).dt.date
    df = df.sort_values("measured_on").drop_duplicates("measured_on", keep="last")
    initial = float(df.iloc[0]["weight_kg"])
    current = float(df.iloc[-1]["weight_kg"])
    current_bmi = bmi(current, height_cm)
    goal_bmi = bmi(goal_weight_kg, height_cm)
    denom = initial - goal_weight_kg
    progress = ((initial - current) / denom * 100.0) if denom > 0 else 0.0
    progress = max(0.0, min(150.0, progress))

    if len(df) < 4:
        return Projection(
            False,
            f"Faltan {4-len(df)} medición(es) semanal(es) para activar la proyección.",
            progress_pct=progress,
            bmi_current=current_bmi,
            bmi_goal=goal_bmi,
        )

    span_days = (df.iloc[3]["measured_on"] - df.iloc[0]["measured_on"]).days
    if span_days < 18:
        return Projection(
            False,
            "Ya hay 4 registros, pero deben cubrir aproximadamente 4 semanas para proyectar con mayor estabilidad.",
            progress_pct=progress,
            bmi_current=current_bmi,
            bmi_goal=goal_bmi,
        )

    first4 = df.iloc[:4].copy()
    first4_slope = _theil_sen_slope_per_day(first4)
    first4_week = first4_slope * 7 if first4_slope is not None else None

    # Proyección viva: usa hasta las últimas 8 mediciones para adaptarse sin sobrerreaccionar a un solo peso.
    recent = df.tail(8).copy()
    slope_day = _theil_sen_slope_per_day(recent)
    if slope_day is None:
        return Projection(False, "No fue posible calcular una tendencia con los registros disponibles.")

    pace_week = slope_day * 7.0
    if current <= goal_weight_kg:
        return Projection(
            True,
            "Objetivo alcanzado o superado.",
            pace_kg_week=pace_week,
            projected_date=df.iloc[-1]["measured_on"],
            weeks_to_goal=0.0,
            progress_pct=100.0,
            bmi_current=current_bmi,
            bmi_goal=goal_bmi,
            first_four_pace_kg_week=first4_week,
        )

    if pace_week >= -0.05:
        return Projection(
            True,
            "La tendencia actual no permite estimar una fecha de llegada al objetivo. Se necesita una tendencia descendente sostenida.",
            pace_kg_week=pace_week,
            projected_date=None,
            weeks_to_goal=None,
            progress_pct=progress,
            bmi_current=current_bmi,
            bmi_goal=goal_bmi,
            first_four_pace_kg_week=first4_week,
        )

    weeks = (current - goal_weight_kg) / abs(pace_week)
    last_date = df.iloc[-1]["measured_on"]
    projected = last_date + timedelta(days=int(round(weeks * 7)))
    return Projection(
        True,
        "Proyección activa basada en tu tendencia observada.",
        pace_kg_week=pace_week,
        projected_date=projected,
        weeks_to_goal=weeks,
        progress_pct=progress,
        bmi_current=current_bmi,
        bmi_goal=goal_bmi,
        first_four_pace_kg_week=first4_week,
    )


def mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, sex: str) -> Optional[float]:
    sex = (sex or "").lower()
    if sex not in {"hombre", "mujer"}:
        return None
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "hombre" else base - 161


def tdee_estimate(weight_kg: float, height_cm: float, age: int, sex: str, activity: str) -> Optional[float]:
    ree = mifflin_st_jeor(weight_kg, height_cm, age, sex)
    if ree is None:
        return None
    factors = {
        "Sedentario": 1.20,
        "Ligero": 1.375,
        "Moderado": 1.55,
        "Alto": 1.725,
        "Muy alto": 1.90,
    }
    return ree * factors.get(activity, 1.20)


# ============================================================
# NUTRICIÓN + ACTIVIDAD DIARIA
# ============================================================

STRENGTH_METS = {
    # 2024 Adult Compendium of Physical Activities:
    # body-weight resistance general ~= 3.0 MET
    # resistance training, multiple exercises ~= 3.5 MET
    # circuit / vigorous resistance ~= 5.8 MET
    "Suave": 3.0,
    "Moderado": 3.5,
    "Intenso": 5.8,
}


def kcal_from_met(
    weight_kg: float,
    minutes: float,
    met: float,
    subtract_resting_met: bool = True,
) -> float:
    """
    Estima kcal a partir de MET:
        kcal/min = MET * 3.5 * kg / 200

    Como Virgils Journey ya parte de un gasto basal/sedentario, por defecto
    resta 1 MET para reducir doble conteo de la energía de reposo.
    """
    if weight_kg <= 0 or minutes <= 0 or met <= 0:
        return 0.0

    effective_met = max(met - 1.0, 0.0) if subtract_resting_met else met
    return effective_met * 3.5 * weight_kg / 200.0 * minutes


def steps_expenditure_kcal(
    weight_kg: float,
    steps: int,
    cadence_steps_min: float = 100.0,
    walking_met: float = 3.5,
) -> float:
    """
    Aproximación del gasto EXTRA asociado a pasos.

    Al no disponer de velocidad/cadencia reales, asume ~100 pasos/min y
    caminata moderada ~3.5 MET. Se resta 1 MET para no duplicar el reposo.
    """
    if steps <= 0 or cadence_steps_min <= 0:
        return 0.0
    minutes = float(steps) / cadence_steps_min
    return kcal_from_met(weight_kg, minutes, walking_met, subtract_resting_met=True)


def strength_expenditure_kcal(
    weight_kg: float,
    minutes: float,
    intensity: str = "Moderado",
) -> float:
    met = STRENGTH_METS.get(intensity, STRENGTH_METS["Moderado"])
    return kcal_from_met(weight_kg, minutes, met, subtract_resting_met=True)


def daily_expenditure_with_activity(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    steps: int = 0,
    strength_minutes: float = 0.0,
    strength_intensity: str = "Moderado",
) -> Optional[dict]:
    """
    Gasto diario aproximado:
      REE Mifflin-St Jeor x 1.20 (base sedentaria)
      + gasto extra por pasos
      + gasto extra por fuerza.

    Usa una base sedentaria deliberadamente para evitar contar dos veces la
    actividad cuando el usuario registra pasos y entrenamiento explícitamente.
    """
    ree = mifflin_st_jeor(weight_kg, height_cm, age, sex)
    if ree is None:
        return None

    baseline = ree * 1.20
    steps_kcal = steps_expenditure_kcal(weight_kg, int(steps or 0))
    strength_kcal = strength_expenditure_kcal(
        weight_kg,
        float(strength_minutes or 0.0),
        strength_intensity,
    )
    total = baseline + steps_kcal + strength_kcal

    return {
        "ree_kcal": float(ree),
        "baseline_kcal": float(baseline),
        "steps_kcal": float(steps_kcal),
        "strength_kcal": float(strength_kcal),
        "total_kcal": float(total),
    }


@dataclass
class BehaviorProjection:
    ready: bool
    message: str
    avg_intake_kcal: Optional[float] = None
    avg_expenditure_kcal: Optional[float] = None
    avg_deficit_kcal_day: Optional[float] = None
    theoretical_pace_kg_week: Optional[float] = None
    projected_date: Optional[date] = None
    weeks_to_goal: Optional[float] = None


def behavior_projection_from_energy_balance(
    current_weight_kg: float,
    goal_weight_kg: float,
    avg_intake_kcal: float,
    avg_expenditure_kcal: float,
    as_of: Optional[date] = None,
    min_valid_days: int = 4,
    valid_days: int = 0,
) -> BehaviorProjection:
    """
    Proyección secundaria basada en balance energético REGISTRADO.

    Usa ~7.700 kcal/kg solo como aproximación operativa; no sustituye la
    proyección principal basada en el peso observado y no modela adaptaciones
    metabólicas individuales.
    """
    as_of = as_of or date.today()

    if valid_days < min_valid_days:
        return BehaviorProjection(
            False,
            f"Registra nutrición al menos {min_valid_days} días para activar la proyección por hábitos.",
        )

    if avg_expenditure_kcal <= 0 or avg_intake_kcal < 0:
        return BehaviorProjection(False, "No hay datos energéticos suficientes para proyectar.")

    deficit = avg_expenditure_kcal - avg_intake_kcal

    if current_weight_kg <= goal_weight_kg:
        return BehaviorProjection(
            True,
            "Objetivo alcanzado o superado.",
            avg_intake_kcal=avg_intake_kcal,
            avg_expenditure_kcal=avg_expenditure_kcal,
            avg_deficit_kcal_day=deficit,
            theoretical_pace_kg_week=0.0,
            projected_date=as_of,
            weeks_to_goal=0.0,
        )

    if deficit <= 100:
        return BehaviorProjection(
            True,
            "El balance energético registrado no muestra un déficit suficiente para estimar descenso sostenido.",
            avg_intake_kcal=avg_intake_kcal,
            avg_expenditure_kcal=avg_expenditure_kcal,
            avg_deficit_kcal_day=deficit,
            theoretical_pace_kg_week=0.0,
        )

    pace = deficit * 7.0 / 7700.0
    if pace <= 0:
        return BehaviorProjection(
            True,
            "No es posible estimar una fecha con el balance actual.",
            avg_intake_kcal=avg_intake_kcal,
            avg_expenditure_kcal=avg_expenditure_kcal,
            avg_deficit_kcal_day=deficit,
            theoretical_pace_kg_week=pace,
        )

    weeks = (current_weight_kg - goal_weight_kg) / pace
    projected = as_of + timedelta(days=int(round(weeks * 7.0)))

    return BehaviorProjection(
        True,
        "Proyección secundaria basada en nutrición y actividad registradas.",
        avg_intake_kcal=avg_intake_kcal,
        avg_expenditure_kcal=avg_expenditure_kcal,
        avg_deficit_kcal_day=deficit,
        theoretical_pace_kg_week=pace,
        projected_date=projected,
        weeks_to_goal=weeks,
    )

