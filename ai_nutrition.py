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



def _daily_guidance_prompt(context: dict[str, Any]) -> str:
    meals = context.get("meals") or []
    meals_text = "\n".join(
        f"- {m.get('description','Comida')}: {m.get('calories_kcal',0):.0f} kcal, "
        f"{m.get('protein_g',0):.0f} g proteína, {m.get('carbs_g',0):.0f} g carbos, "
        f"{m.get('fat_g',0):.0f} g grasas"
        for m in meals
    ) or "- Aún no hay comidas registradas."

    return f"""
Eres el coach nutricional de Virgils Journey. Tu tarea es analizar el día ACTUAL
con datos ya calculados por la aplicación y sugerir próximas comidas prácticas.
No diagnostiques ni sustituyas consejo médico. No propongas ayunos extremos,
castigos con ejercicio ni déficits mayores al objetivo entregado por la app.

DATOS DEL DÍA
- Calorías consumidas: {context.get('consumed_kcal',0):.0f} kcal
- Proteína consumida: {context.get('protein_g',0):.0f} g
- Carbohidratos consumidos: {context.get('carbs_g',0):.0f} g
- Grasas consumidas: {context.get('fat_g',0):.0f} g
- Gasto estimado: {context.get('expenditure_kcal',0):.0f} kcal
- Déficit objetivo: {context.get('target_deficit_kcal',0):.0f} kcal
- Presupuesto calórico del día: {context.get('calorie_target_kcal',0):.0f} kcal
- Calorías aproximadas disponibles: {context.get('remaining_kcal',0):.0f} kcal
- Meta de proteína orientativa: {context.get('protein_target_g',0):.0f} g
- Proteína faltante aproximada: {context.get('remaining_protein_g',0):.0f} g
- Pasos: {context.get('steps',0)}
- Fuerza: {context.get('strength_minutes',0)} min ({context.get('strength_intensity','Moderado')})
- Notas de actividad: {context.get('activity_notes','') or 'Sin notas'}

COMIDAS REGISTRADAS
{meals_text}

REGLAS
1. Evalúa si el registro parece incompleto antes de concluir que existe un déficit muy alto.
2. Prioriza completar proteína, fibra, verduras/frutas y saciedad sin superar innecesariamente el presupuesto.
3. Sugiere 2 o 3 opciones de próxima comida fáciles de conseguir/preparar en Chile/Latinoamérica.
4. Cada opción debe incluir kcal aproximadas y proteína aproximada.
5. Si quedan pocas calorías, no recomiendes saltarse comidas; propone una opción pequeña y nutritiva.
6. Si ya se superó el presupuesto, propone una siguiente comida moderada y equilibrada, sin compensaciones extremas.
7. Sé breve, concreto y accionable.
8. Devuelve SOLO JSON válido, sin markdown.

FORMATO JSON EXACTO
{{
  "status": "bien|atencion|incompleto",
  "headline": "frase de máximo 12 palabras",
  "analysis": "2 a 4 frases breves",
  "next_meals": [
    {{"name":"...", "kcal":0, "protein_g":0, "reason":"..."}},
    {{"name":"...", "kcal":0, "protein_g":0, "reason":"..."}}
  ],
  "activity_note": "1 frase sobre pasos/fuerza y cómo encajan hoy",
  "warning": "mensaje breve si el registro parece incompleto; de lo contrario cadena vacía"
}}
""".strip()


def _normalize_guidance(data: dict[str, Any], provider: str) -> dict[str, Any]:
    status = str(data.get("status") or "bien").strip().lower()
    if status not in {"bien", "atencion", "incompleto"}:
        status = "bien"

    meals_out = []
    for item in (data.get("next_meals") or [])[:3]:
        if not isinstance(item, dict):
            continue
        meals_out.append({
            "name": str(item.get("name") or "Opción equilibrada").strip(),
            "kcal": max(0, _to_int(item.get("kcal"))),
            "protein_g": max(0.0, round(_to_float(item.get("protein_g")), 1)),
            "reason": str(item.get("reason") or "").strip(),
        })

    return {
        "status": status,
        "headline": str(data.get("headline") or "Balance del día").strip(),
        "analysis": str(data.get("analysis") or "").strip(),
        "next_meals": meals_out,
        "activity_note": str(data.get("activity_note") or "").strip(),
        "warning": str(data.get("warning") or "").strip(),
        "provider": provider,
    }


def _try_gemini_guidance(prompt: str, api_key: str, model: str) -> dict[str, Any]:
    client = genai.Client(api_key=api_key.strip())
    last_error: Exception | None = None
    for attempt in range(GEMINI_ATTEMPTS):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            text = getattr(response, "text", None) or ""
            return _normalize_guidance(_extract_json(text), f"Gemini · {model}")
        except Exception as exc:
            last_error = exc
            if attempt < GEMINI_ATTEMPTS - 1 and _is_transient_error(exc):
                time.sleep(1.0 + random.uniform(0.2, 0.8))
                continue
            raise
    raise last_error or RuntimeError("Gemini no respondió.")


def _try_openrouter_guidance(prompt: str, api_key: str, model: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://virgilsjourney.streamlit.app",
        "X-Title": "Virgils Journey",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Responde únicamente con JSON válido."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.25,
    }
    last_error: Exception | None = None
    for attempt in range(OPENROUTER_ATTEMPTS):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
            if response.status_code >= 400:
                raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text[:1200]}")
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError("OpenRouter no devolvió una respuesta utilizable.")
            content = choices[0].get("message", {}).get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    str(x.get("text", "")) if isinstance(x, dict) else str(x)
                    for x in content
                )
            return _normalize_guidance(_extract_json(str(content)), f"OpenRouter · {model}")
        except Exception as exc:
            last_error = exc
            if attempt < OPENROUTER_ATTEMPTS - 1 and _is_transient_error(exc):
                time.sleep((1.5 * (attempt + 1)) + random.uniform(0.2, 0.8))
                continue
            raise
    raise last_error or RuntimeError("OpenRouter no respondió.")


def analyze_daily_balance(
    context: dict[str, Any],
    gemini_api_key: str = "",
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    openrouter_api_key: str = "",
    openrouter_model: str = DEFAULT_OPENROUTER_MODEL,
) -> dict[str, Any]:
    """Analiza el balance del día y sugiere próximas comidas con fallback de proveedor."""
    if not str(gemini_api_key or "").strip() and not str(openrouter_api_key or "").strip():
        raise ValueError("No hay ningún proveedor de IA configurado.")

    prompt = _daily_guidance_prompt(context)
    errors: list[str] = []

    if str(gemini_api_key or "").strip():
        try:
            return _try_gemini_guidance(prompt, gemini_api_key, gemini_model or DEFAULT_GEMINI_MODEL)
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

    if str(openrouter_api_key or "").strip():
        try:
            return _try_openrouter_guidance(prompt, openrouter_api_key, openrouter_model or DEFAULT_OPENROUTER_MODEL)
        except Exception as exc:
            errors.append(f"OpenRouter: {exc}")

    detail = " | ".join(errors[-2:])
    raise RuntimeError(
        "No fue posible generar el análisis del día en este momento."
        + (f" Detalle técnico: {detail}" if detail else "")
    )
