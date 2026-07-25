import google.generativeai as genai
import os
import glob
import json
import requests
import sys

# Configuracion de variables de entorno
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY no encontrada. Omitiendo diagnostico IA.")
    sys.exit(0)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def send_to_slack(message):
    if not SLACK_WEBHOOK_URL:
        print("⚠️ SLACK_WEBHOOK_URL no configurado. Mensaje solo en consola:")
        print(message)
        return
        
    payload = {
        "text": message
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if response.status_code != 200:
        print(f"Error al enviar mensaje a Slack: {response.text}")

def run_diagnostics():
    # Buscar archivos HTML de errores
    files = glob.glob("build/debug-artifacts/*.html")
    
    if not files:
        print("🔍 No se encontraron artefactos de debug para analizar.")
        return

    # Intentar leer la skill de Locators si existe
    skill_context = ""
    skill_path = ".agent/skills/selenium-stability-specialist/selenium-stability-specialist.MD"
    if os.path.exists(skill_path):
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_context = f.read()

    for file_path in files:
        scenario_name = os.path.basename(file_path).replace("dom_dump_", "").replace(".html", "")
        print(f"🤖 Analizando fallo para el escenario: {scenario_name}...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            # Truncar el HTML si es muy grande (Gemini Flash soporta mucho, pero por precaucion)
            if len(html_content) > 500000:
                html_content = html_content[:500000]

        prompt = f"""
        Eres un experto Senior QA Automation Engineer y especialista en establidad de Selenium.
        
        TUS REGLAS Y ESTRATEGIAS ESTRICTAS DE LOCALIZADORES (SIGUE ESTO EXACTAMENTE):
        ---
        {skill_context}
        ---

        Se ha detectado un fallo en el test: {scenario_name}.
        Por desgracia, no tengo el StackTrace exacto de JUnit a mano, pero asume que *un elemento no se encontro o no se pudo interactuar (NoSuchElementException, TimeoutException)*.

        Aqui tienes el DOM/HTML de la pagina en el momento exacto del fallo:
        ---
        {html_content}
        ---
        
        Tu tarea:
        1. Analiza el DOM dado. Considera que es tipicamente un error de localizador.
        2. Determina que elementos podrian estar fallando (ej. falta de ids, elementos dinamicos).
        3. Elabora un reporte CORTO proponiendo cual podria ser el elemento objetivo fallido (ej: login button, form submit, etc.) y sugiere un nuevo localizado robusto siguiendo estrictamente tus reglas de la Skill de Locators dada en tu contexto.
        
        Da tu respuesta en el siguiente formato amigable para Slack:
        🚨 *FALLO DETECTADO EN TEST:* {scenario_name}
        *Posible causa analizada por IA:* [Breve descripcion]
        *Nuevo Elemento/Locator Sugerido:* [Locator o codigo Java sugerido]
        """

        try:
            response = model.generate_content(prompt)
            send_to_slack(response.text)
        except Exception as e:
            print(f"❌ Error al consultar la API de Gemini: {e}")

if __name__ == "__main__":
    run_diagnostics()
