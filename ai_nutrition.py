from __future__ import annotations

import json
import random
import re
import time
from typing import Any

from google import genai


DEFAULT_MODEL = "gemini-3.6-flash"
MAX_ATTEMPTS = 4


def _extract_json(text: str) -> dict[str, Any]:
    """
    Extrae un objeto JSON aunque Gemini lo devuelva dentro de ```json ... ```.
    """
    if not text:
        raise ValueError("Gemini no devolvió contenido.")

    cleaned = text.strip()

    # Quitar fences markdown
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Intento de rescate: tomar desde la primera { hasta la última }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("La respuesta de Gemini no contiene un JSON válido.")
        data = json.loads(cleaned[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("Gemini devolvió un formato inesperado.")

    return data


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)

    txt = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", txt)
    return float(match.group()) if match else default


def _to_int(value: Any, default: int = 0) -> int:
    return int(round(_to_float(value, float(default))))


def _normalize_result(data: dict[str, Any]) -> dict[str, Any]:
    """
    Devuelve exactamente las claves que espera streamlit_app.py.
    """
    calories = max(0, _to_int(data.get("calories_kcal")))
    protein = max(0.0, _to_float(data.get("protein_g")))
    carbs = max(0.0, _to_float(data.get("carbs_g")))
    fat = max(0.0, _to_float(data.get("fat_g")))

    summary = str(data.get("summary") or "").strip()
    confidence = str(data.get("confidence") or "media").strip().lower()

    if confidence not in {"alta", "media", "baja"}:
        confidence = "media"

    # Control básico de coherencia energética.
    # No corrige automáticamente; solo añade una advertencia al resumen.
    macro_kcal = protein * 4 + carbs * 4 + fat * 9
    if calories > 0 and macro_kcal > 0:
        diff = abs(calories - macro_kcal) / max(calories, 1)
        if diff > 0.35:
            warning = (
                "Nota: la estimación de calorías y macronutrientes tiene una "
                "diferencia relevante; revisa porciones, preparación y aceites."
            )
            summary = f"{summary} {warning}".strip()

    return {
        "calories_kcal": calories,
        "protein_g": round(protein, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "summary": summary,
        "confidence": confidence,
    }


def _is_transient_error(exc: Exception) -> bool:
    """
    Errores que normalmente conviene reintentar:
    429 = rate limit
    500/502/503/504 = fallo temporal / alta demanda
    """
    message = str(exc).upper()

    transient_markers = (
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "502",
        "503",
        "504",
        "UNAVAILABLE",
        "DEADLINE_EXCEEDED",
        "INTERNAL",
        "HIGH DEMAND",
        "TEMPORAR",
    )
    return any(marker in message for marker in transient_markers)


def estimate_with_gemini(
    food_text: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    fallback_models: list[str] | None = None,
) -> dict[str, Any]:
    """
    Estima calorías y macros usando Gemini.

    Compatible con la llamada actual de streamlit_app.py:
        estimate_with_gemini(text, api_key, model)

    Reintenta automáticamente los errores transitorios con exponential backoff.
    Puedes pasar modelos alternativos mediante fallback_models si en el futuro
    quieres habilitar un fallback explícito.
    """
    if not api_key or not str(api_key).strip():
        raise ValueError("GEMINI_API_KEY no está configurada.")

    if not food_text or not food_text.strip():
        raise ValueError("Debes describir lo que comiste.")

    client = genai.Client(api_key=api_key.strip())

    prompt = f"""
Eres un asistente de estimación nutricional para una aplicación de seguimiento
personal. Analiza SOLO la comida descrita por el usuario.

COMIDA:
{food_text.strip()}

OBJETIVO:
Estimar el total aproximado de:
- calorías (kcal)
- proteínas (g)
- carbohidratos (g)
- grasas (g)

REGLAS:
1. Interpreta unidades habituales en español y alimentos comunes en Chile/Latinoamérica.
2. Si una porción es ambigua, usa una porción estándar razonable y dilo en summary.
3. Considera preparación, aceites, salsas y acompañamientos solo cuando estén mencionados
   o sean claramente necesarios para la preparación descrita.
4. No inventes ingredientes específicos que el usuario no mencionó.
5. Si faltan cantidades, entrega una estimación prudente e indica que la confianza es baja.
6. No des diagnóstico médico.
7. Devuelve SOLO un objeto JSON válido, sin markdown, comentarios ni texto adicional.

FORMATO JSON EXACTO:
{{
  "calories_kcal": 0,
  "protein_g": 0.0,
  "carbs_g": 0.0,
  "fat_g": 0.0,
  "confidence": "alta|media|baja",
  "summary": "Breve explicación de supuestos y porciones usadas."
}}
""".strip()

    models_to_try = [model]
    if fallback_models:
        for fallback in fallback_models:
            if fallback and fallback not in models_to_try:
                models_to_try.append(fallback)

    last_error: Exception | None = None

    for model_name in models_to_try:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                response_text = getattr(response, "text", None)
                data = _extract_json(response_text or "")
                return _normalize_result(data)

            except Exception as exc:
                last_error = exc

                if not _is_transient_error(exc):
                    raise RuntimeError(
                        f"No fue posible obtener la estimación con Gemini: {exc}"
                    ) from exc

                # Exponential backoff + jitter:
                # aprox. 1-2 s, 2-3 s, 4-5 s, 8-9 s
                if attempt < MAX_ATTEMPTS - 1:
                    wait_seconds = (2 ** attempt) + random.uniform(0.4, 1.2)
                    time.sleep(wait_seconds)

    raise RuntimeError(
        "Gemini está temporalmente con alta demanda. "
        "Virgils Journey reintentó automáticamente varias veces, pero el servicio "
        "sigue ocupado. Inténtalo nuevamente en unos minutos."
    ) from last_error
