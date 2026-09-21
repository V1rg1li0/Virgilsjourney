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


def _food_context_hint(food_text: str) -> str:
    """Genera pistas contextuales simples para reducir errores de interpretación."""
    txt = (food_text or "").strip().lower()
    hints: list[str] = []

    # En Chile/LatAm es frecuente decir "20/25 rolls" para referirse a piezas de sushi.
    # Solo asumimos rollos completos si el usuario lo expresa explícitamente.
    sushi_count = re.search(r"\b(\d{1,3})\s*(?:rolls?|roles?)\b", txt)
    if sushi_count and any(word in txt for word in ("sushi", "salm", "kanikama", "camar", "palmit")):
        n = sushi_count.group(1)
        if not re.search(r"\b(?:rollos?|rolls?)\s+complet", txt):
            hints.append(
                f'La frase "{n} rolls" aparece en contexto de sushi. '
                f'Interprétala por defecto como {n} piezas/unidades de sushi, NO como {n} rollos completos, '
                'salvo evidencia explícita en el texto.'
            )

    return "\n".join(f"- {h}" for h in hints)


def _nutrition_prompt(food_text: str) -> str:
    context_hint = _food_context_hint(food_text)
    return f"""
Eres un asistente de estimación nutricional para Virgils Journey.
Analiza SOLO la comida descrita por el usuario y estima una ingesta REALISTA.

COMIDA:
{food_text.strip()}

PISTAS CONTEXTUALES AUTOMÁTICAS:
{context_hint or '- Sin pistas adicionales.'}

OBJETIVO:
Estimar el total aproximado de:
- calorías (kcal)
- proteínas (g)
- carbohidratos (g)
- grasas (g)

REGLAS DE INTERPRETACIÓN:
1. Interpreta lenguaje cotidiano de Chile/Latinoamérica, no solo traducciones literales.
2. Distingue cuidadosamente entre PIEZAS, PORCIONES, ROLLOS COMPLETOS, PLATOS, TAZAS, CUCHARADAS, etc.
3. En sushi, expresiones como "20 rolls", "25 rolls" o "30 rolls" suelen usarse coloquialmente para referirse a piezas/unidades. NO multipliques como si fueran 20/25/30 rollos completos, salvo que el usuario diga explícitamente "rollos completos", "rollos enteros" o equivalente.
4. Si una cantidad es ambigua pero existe una interpretación cotidiana claramente más probable, usa esa interpretación y explícala en `interpretation` y `summary`.
5. Si hay dos interpretaciones igualmente plausibles y cambian mucho el resultado, usa la más conservadora y marca `confidence` como "baja".
6. No inventes queso crema, fritura, tempura, mayonesa, salsas, bebidas, aceites ni acompañamientos si no fueron mencionados. Si son imprescindibles para una preparación típica, usa una cantidad moderada y dilo.
7. Si faltan tamaños/pesos, utiliza porciones estándar razonables; evita extremos.
8. Haz una comprobación de plausibilidad antes de responder. Una sola comida corriente no debería terminar en miles de kcal o cientos de gramos de proteína sin que el texto lo justifique claramente.
9. Comprueba coherencia energética aproximada: proteína*4 + carbohidratos*4 + grasas*9 debe ser razonablemente compatible con las kcal totales.
10. No des diagnóstico médico.
11. Devuelve SOLO un objeto JSON válido, sin markdown ni texto adicional.

FORMATO JSON EXACTO:
{{
  "calories_kcal": 0,
  "protein_g": 0.0,
  "carbs_g": 0.0,
  "fat_g": 0.0,
  "confidence": "alta|media|baja",
  "interpretation": "Qué cantidad/unidad entendiste y principales supuestos.",
  "summary": "Breve explicación de la estimación y supuestos."
}}
""".strip()


def _correction_prompt(food_text: str, initial: dict[str, Any]) -> str:
    """Segundo pase cuando el primer resultado no parece plausible."""
    return f"""
Revisa y CORRIGE una estimación nutricional que fue marcada como potencialmente no plausible.

COMIDA ORIGINAL:
{food_text.strip()}

ESTIMACIÓN ANTERIOR:
{json.dumps(initial, ensure_ascii=False)}

PISTAS:
{_food_context_hint(food_text) or '- Sin pistas adicionales.'}

INSTRUCCIONES:
1. Reinterpreta desde cero las cantidades y unidades del usuario.
2. Si aparece una cantidad seguida de "roll/rolls" en contexto de sushi y NO dice explícitamente rollos completos/enteros, interprétala como número de piezas de sushi.
3. Evita multiplicaciones implícitas que transformen piezas en rollos completos.
4. Usa porciones habituales en Chile/Latinoamérica y valores nutricionales razonables.
5. Verifica que proteína*4 + carbohidratos*4 + grasas*9 sea compatible con las calorías.
6. Si la comida realmente pudiera ser extraordinariamente grande, solo conserva un valor extremo si el texto lo justifica de forma inequívoca.
7. Devuelve SOLO JSON válido.

FORMATO JSON EXACTO:
{{
  "calories_kcal": 0,
  "protein_g": 0.0,
  "carbs_g": 0.0,
  "fat_g": 0.0,
  "confidence": "alta|media|baja",
  "interpretation": "Qué cantidad/unidad entendiste y principales supuestos.",
  "summary": "Breve explicación de la estimación corregida."
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

    interpretation = str(data.get("interpretation") or "").strip()
    summary = str(data.get("summary") or "").strip()
    confidence = str(data.get("confidence") or "media").strip().lower()
    if confidence not in {"alta", "media", "baja"}:
        confidence = "media"

    macro_kcal = protein * 4 + carbs * 4 + fat * 9
    macro_diff_pct = None
    if calories > 0 and macro_kcal > 0:
        macro_diff_pct = abs(calories - macro_kcal) / max(calories, 1)
        if macro_diff_pct > 0.25:
            confidence = "baja"
            note = (
                "La relación entre calorías y macronutrientes tiene una diferencia relevante; "
                "la estimación fue marcada para revisión."
            )
            summary = f"{summary} {note}".strip()

    if interpretation:
        summary = f"Interpretación: {interpretation}. {summary}".strip()

    return {
        "calories_kcal": calories,
        "protein_g": round(protein, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "summary": summary,
        "interpretation": interpretation,
        "confidence": confidence,
        "provider": provider,
        "macro_kcal": round(macro_kcal, 1),
        "macro_diff_pct": round(macro_diff_pct, 3) if macro_diff_pct is not None else None,
    }


def _looks_implausible(food_text: str, result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Detecta salidas extremas o internamente incoherentes antes de mostrarlas."""
    calories = float(result.get("calories_kcal") or 0)
    protein = float(result.get("protein_g") or 0)
    carbs = float(result.get("carbs_g") or 0)
    fat = float(result.get("fat_g") or 0)
    macro_diff = result.get("macro_diff_pct")

    reasons: list[str] = []
    txt = (food_text or "").lower()

    # Límites deliberadamente amplios: no pretenden decir cuánto "debe" comer el usuario,
    # solo evitar errores obvios de escala/unidades del modelo.
    if calories > 3500:
        reasons.append("calorías extraordinariamente altas para una sola descripción")
    if protein > 250:
        reasons.append("proteína extraordinariamente alta")
    if carbs > 500:
        reasons.append("carbohidratos extraordinariamente altos")
    if fat > 220:
        reasons.append("grasas extraordinariamente altas")
    if macro_diff is not None and float(macro_diff) > 0.35:
        reasons.append("calorías y macros no son coherentes")

    # Protección específica contra el error observado: N "rolls" de sushi tratados como N rollos enteros.
    sushi_count = re.search(r"\b(\d{1,3})\s*(?:rolls?|roles?)\b", txt)
    if sushi_count and any(word in txt for word in ("sushi", "salm", "kanikama", "camar", "palmit")):
        n = int(sushi_count.group(1))
        explicit_full_rolls = bool(re.search(r"\b(?:rollos?|rolls?)\s+(?:complet|enter)", txt))
        if not explicit_full_rolls and n <= 60 and calories > max(3000, n * 140):
            reasons.append("posible confusión entre piezas de sushi y rollos completos")

    return bool(reasons), reasons


def _validate_or_raise(food_text: str, result: dict[str, Any]) -> dict[str, Any]:
    bad, reasons = _looks_implausible(food_text, result)
    if bad:
        raise ValueError("Estimación no plausible: " + "; ".join(reasons))
    return result

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
            response = client.models.generate_content(model=model, contents=prompt)
            raw = _extract_json(getattr(response, "text", None) or "")
            result = _normalize_result(raw, f"Gemini · {model}")

            bad, reasons = _looks_implausible(food_text, result)
            if bad:
                correction = client.models.generate_content(
                    model=model,
                    contents=_correction_prompt(food_text, raw),
                )
                corrected_raw = _extract_json(getattr(correction, "text", None) or "")
                corrected = _normalize_result(corrected_raw, f"Gemini · {model} · verificado")
                return _validate_or_raise(food_text, corrected)

            return result
        except Exception as exc:
            last_error = exc
            if attempt < GEMINI_ATTEMPTS - 1 and _is_transient_error(exc):
                time.sleep(1.0 + random.uniform(0.2, 0.8))
                continue
            raise

    raise last_error or RuntimeError("Gemini no respondió.")

def _openrouter_json(prompt: str, api_key: str, model: str) -> dict[str, Any]:
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
                    "Eres un estimador nutricional cuidadoso. Responde únicamente con JSON válido, "
                    "revisa unidades y evita errores de escala."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.15,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=45,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text[:1200]}")

    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter no devolvió una respuesta utilizable.")

    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "\n".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
        )
    return _extract_json(str(content))


def _try_openrouter(
    food_text: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(OPENROUTER_ATTEMPTS):
        try:
            raw = _openrouter_json(_nutrition_prompt(food_text), api_key, model)
            result = _normalize_result(raw, f"OpenRouter · {model}")

            bad, reasons = _looks_implausible(food_text, result)
            if bad:
                corrected_raw = _openrouter_json(_correction_prompt(food_text, raw), api_key, model)
                corrected = _normalize_result(
                    corrected_raw,
                    f"OpenRouter · {model} · verificado",
                )
                return _validate_or_raise(food_text, corrected)

            return result

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
    Estimación nutricional con validación de plausibilidad y fallback automático.

    Orden:
    1) Gemini. Si la salida parece absurda, hace un segundo pase de corrección.
    2) OpenRouter si Gemini falla o la estimación corregida sigue siendo no plausible.

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
- Hora local actual: {context.get('current_local_time','')}
- ¿Ayuno intermitente?: {'Sí' if context.get('intermittent_fasting') else 'No'}
- Rango habitual de comidas: {context.get('meal_window_start','08:00')}–{context.get('meal_window_end','21:00')}
- Estado respecto al rango: {context.get('meal_window_status','within')}
- Porcentaje aproximado transcurrido de la ventana: {context.get('meal_window_elapsed_pct',0):.0f}%
- Calorías consumidas: {context.get('consumed_kcal',0):.0f} kcal
- Proteína consumida: {context.get('protein_g',0):.0f} g
- Carbohidratos consumidos: {context.get('carbs_g',0):.0f} g
- Grasas consumidas: {context.get('fat_g',0):.0f} g
- Gasto estimado: {context.get('expenditure_kcal',0):.0f} kcal
- Balance aparente hasta este momento: {context.get('apparent_deficit_so_far',0):+.0f} kcal
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
1. La hora y el rango habitual de comidas son obligatorios para interpretar el día.
2. Si el estado es "before", NO marques el registro como incompleto ni emitas warning por pocas calorías: la ventana de alimentación aún no comienza.
3. Si el estado es "within", interpreta el balance como "hasta este momento". NO lo llames déficit final ni emitas warning solo porque el consumo aún es bajo. Recomienda cómo distribuir lo que queda dentro de las horas restantes.
4. Si el estado es "after", recién entonces puedes evaluar si el consumo total parece demasiado bajo o si faltan comidas por registrar.
5. Si hay ayuno intermitente, respeta el rango indicado y no sugieras comer fuera de él salvo que el usuario ya lo haya superado o exista una razón de seguridad clara. No promuevas ayunos más largos.
6. Prioriza completar proteína, fibra, verduras/frutas y saciedad sin superar innecesariamente el presupuesto.
7. Sugiere 2 o 3 opciones de próxima comida fáciles de conseguir/preparar en Chile/Latinoamérica, coherentes con la hora actual y el tiempo restante de la ventana.
8. Cada opción debe incluir kcal aproximadas y proteína aproximada.
9. Si quedan pocas calorías, no recomiendes saltarse comidas; propone una opción pequeña y nutritiva.
10. Si ya se superó el presupuesto, propone una siguiente comida moderada y equilibrada, sin compensaciones extremas.
11. Sé breve, concreto y accionable.
12. Devuelve SOLO JSON válido, sin markdown.

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
