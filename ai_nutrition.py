from __future__ import annotations
import json
from typing import Dict, Any

SYSTEM = """Eres un estimador nutricional conservador. Devuelve SOLO JSON válido con esta forma:
{"calories_kcal": number, "protein_g": number, "carbs_g": number, "fat_g": number, "confidence": "baja|media|alta", "summary": "texto breve"}.
Si faltan cantidades o preparación, usa supuestos razonables y deja claro en summary que es una estimación. No diagnostiques ni prescribas."""


def estimate_with_gemini(text: str, api_key: str, model: str = "gemini-3.7-flash") -> Dict[str, Any]:
    from google import genai
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM}\n\nComida reportada: {text}",
    )
    raw = (resp.text or "").strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
