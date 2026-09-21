from __future__ import annotations

import json
import random
import re
import time
from typing import Any

import requests
from google import genai


DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"

GEMINI_ATTEMPTS = 2
OPENROUTER_ATTEMPTS = 3
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _nutrition_prompt(food_text: str) -> str:
    return f"""
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


def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("La IA no devolvió contenido.")

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("La respuesta de la IA no contiene un JSON válido.")
        data = json.loads(cleaned[start:end + 1])

    if not isinstance(data, dict):
        raise ValueError("La IA devolvió un formato inesperado.")
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


def _normalize_result(data: dict[str, Any], provider: str) -> dict[str, Any]:
    calories = max(0, _to_int(data.get("calories_kcal")))
    protein = max(0.0, _to_float(data.get("protein_g")))
    carbs = max(0.0, _to_float(data.get("carbs_g")))
    fat = max(0.0, _to_float(data.get("fat_g")))

    summary = str(data.get("summary") or "").strip()
    confidence = str(data.get("confidence") or "media").strip().lower()
    if confidence not in {"alta", "media", "baja"}:
        confidence = "media"

    macro_kcal = protein * 4 + carbs * 4 + fat * 9
    if calories > 0 and macro_kcal > 0:
        diff = abs(calories - macro_kcal) / max(calories, 1)
        if diff > 0.35:
            warning = (
                "Nota: calorías y macronutrientes presentan una diferencia relevante; "
                "revisa porciones, preparación y aceites."
            )
            summary = f"{summary} {warning}".strip()

    return {
        "calories_kcal": calories,
        "protein_g": round(protein, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "summary": summary,
        "confidence": confidence,
        "provider": provider,
    }


def _is_transient_error(exc: Exception) -> bool:
    message = str(exc).upper()
    markers = (
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
        "TIMEOUT",
        "CONNECTION",
    )
    return any(marker in message for marker in markers)


def _try_gemini(
    food_text: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    client = genai.Client(api_key=api_key.strip())
    prompt = _nutrition_prompt(food_text)
    last_error: Exception | None = None

    for attempt in range(GEMINI_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            text = getattr(response, "text", None) or ""
            return _normalize_result(_extract_json(text), f"Gemini · {model}")
        except Exception as exc:
            last_error = exc
            if attempt < GEMINI_ATTEMPTS - 1 and _is_transient_error(exc):
                time.sleep(1.0 + random.uniform(0.2, 0.8))
                continue
            raise

    raise last_error or RuntimeError("Gemini no respondió.")


def _try_openrouter(
    food_text: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    prompt = _nutrition_prompt(food_text)
    last_error: Exception | None = None

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://virgilsjourney.streamlit.app",
        "X-Title": "Virgils Journey",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Responde únicamente con JSON válido y sigue exactamente "
                    "el formato solicitado por el usuario."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    for attempt in range(OPENROUTER_ATTEMPTS):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=45,
            )

            if response.status_code >= 400:
                body = response.text[:1200]
                raise RuntimeError(
                    f"OpenRouter HTTP {response.status_code}: {body}"
                )

            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError("OpenRouter no devolvió una respuesta utilizable.")

            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
            )

            # Algunos proveedores pueden responder content como lista estructurada.
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        text_parts.append(str(item.get("text", "")))
                    else:
                        text_parts.append(str(item))
                content = "\n".join(text_parts)

            return _normalize_result(
                _extract_json(str(content)),
                f"OpenRouter · {model}",
            )

        except Exception as exc:
            last_error = exc
            if attempt < OPENROUTER_ATTEMPTS - 1 and _is_transient_error(exc):
                wait = (1.5 * (attempt + 1)) + random.uniform(0.2, 0.8)
                time.sleep(wait)
                continue
            raise

    raise last_error or RuntimeError("OpenRouter no respondió.")


def estimate_nutrition(
    food_text: str,
    gemini_api_key: str = "",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    openrouter_api_key: str = "",
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL,
) -> dict[str, Any]:
    """
    Estimación nutricional con fallback automático.

    Orden:
    1) Gemini (máximo 2 intentos rápidos)
    2) OpenRouter si Gemini falla o está saturado

    Al menos una de las dos API keys debe estar configurada.
    """
    if not food_text or not food_text.strip():
        raise ValueError("Debes describir lo que comiste.")

    if not str(gemini_api_key or "").strip() and not str(openrouter_api_key or "").strip():
        raise ValueError(
            "No hay ningún proveedor de IA configurado. "
            "Configura GEMINI_API_KEY u OPENROUTER_API_KEY."
        )

    errors: list[str] = []

    if str(gemini_api_key or "").strip():
        try:
            return _try_gemini(
                food_text=food_text,
                api_key=gemini_api_key,
                model=gemini_model or DEFAULT_GEMINI_MODEL,
            )
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

    if str(openrouter_api_key or "").strip():
        try:
            return _try_openrouter(
                food_text=food_text,
                api_key=openrouter_api_key,
                model=openrouter_model or DEFAULT_OPENROUTER_MODEL,
            )
        except Exception as exc:
            errors.append(f"OpenRouter: {exc}")

    detail = " | ".join(errors[-2:])
    raise RuntimeError(
        "Los proveedores de IA no pudieron completar la estimación en este momento. "
        "Inténtalo nuevamente en unos minutos."
        + (f" Detalle técnico: {detail}" if detail else "")
    )


# Compatibilidad con versiones anteriores del streamlit_app.py.
def estimate_with_gemini(
    food_text: str,
    api_key: str,
    model: str = DEFAULT_GEMINI_MODEL,
    fallback_models: list[str] | None = None,
) -> dict[str, Any]:
    return estimate_nutrition(
        food_text=food_text,
        gemini_api_key=api_key,
        gemini_model=model,
    )
