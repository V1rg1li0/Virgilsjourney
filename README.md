# Virgils Journey

App web móvil en Python/Streamlit para control semanal de peso, medidas corporales, proyección hacia una meta y registro nutricional con IA opcional.

## Qué hace

- Registro inicial: edad, estatura, peso, meta, pecho, cintura, cuello y cadera.
- Solicita una medición al menos cada 7 días.
- Tras 4 mediciones distribuidas en aproximadamente 4 semanas activa la proyección.
- La proyección usa una tendencia robusta (mediana de pendientes entre pares de puntos, similar a Theil–Sen) y se actualiza con hasta las últimas 8 mediciones.
- Muestra progreso, ritmo observado y fecha aproximada de llegada a la meta.
- Compara el ritmo observado con la referencia gradual de CDC de ~1–2 lb/semana; no limita ni “prescribe” una velocidad.
- Nutrición: registro manual + estimador IA opcional con Gemini.
- Recordatorio semanal por correo con GitHub Actions + Resend.

## Arquitectura gratuita recomendada

1. **Frontend Python:** Streamlit Community Cloud.
2. **Base de datos + login:** Supabase Free.
3. **IA nutricional:** Gemini API Free Tier (opcional).
4. **Correo:** Resend Free.
5. **Programación del recordatorio:** GitHub Actions, ejecución diaria.

## Instalación local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

Copia `.streamlit/secrets.example.toml` a `.streamlit/secrets.toml` y completa las claves.

```bash
streamlit run streamlit_app.py
```

## Configurar Supabase

1. Crea un proyecto gratuito en Supabase.
2. Abre **SQL Editor** y ejecuta `supabase_schema.sql`.
3. En **Authentication > URL Configuration**, configura luego la URL pública de Streamlit como Site URL.
4. Copia Project URL y anon key a los Secrets de Streamlit.
5. Mantén **service role key** solo en GitHub Secrets. Nunca la expongas en Streamlit.

## Desplegar gratis en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio GitHub.
2. En Streamlit Community Cloud: `Create app` → selecciona repo → `streamlit_app.py`.
3. En **Advanced settings > Secrets**, pega:

```toml
SUPABASE_URL="..."
SUPABASE_ANON_KEY="..."
GEMINI_API_KEY="..." # opcional
GEMINI_MODEL="gemini-3.7-flash"
```

4. Publica la app y vuelve a Supabase para registrar esa URL como Site URL.

## Recordatorios por email

Crea una cuenta Resend, valida un dominio/remitente y agrega estos **GitHub Actions Secrets**:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `RESEND_API_KEY`
- `REMINDER_FROM_EMAIL`
- `APP_URL`

El workflow `.github/workflows/reminders.yml` corre diariamente a las 12:00 UTC y envía recordatorio solo a quienes tengan ese día configurado y no hayan registrado recientemente.

## Metodología y cautelas

La app no diagnostica ni prescribe. La fecha proyectada se basa en tendencia observada y puede cambiar por hidratación, retención de líquidos, cambios de rutina, medicamentos, enfermedad, sueño y otros factores. Pesarse bajo condiciones similares (idealmente mismo día/horario y condiciones comparables) mejora la utilidad del seguimiento.

La estimación de gasto energético usa Mifflin–St Jeor solo cuando el usuario informa sexo para la fórmula y nivel de actividad. Es una aproximación, no calorimetría indirecta.

## Ejemplo del caso inicial

Con 108 kg, 180 cm y meta 95 kg, la app **no proyecta una fecha el primer día**. Después de cuatro mediciones semanales, calcula el ritmo observado. Si, por ejemplo, el ritmo robusto resultara -0,60 kg/semana y el peso actual fuera 106 kg, quedarían 11 kg y la proyección sería de ~18 semanas, actualizándose con nuevas mediciones.
