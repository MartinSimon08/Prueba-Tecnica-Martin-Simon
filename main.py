import os
import json
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pypdf import PdfReader

app = FastAPI()

class Consulta(BaseModel):
    pregunta: str

#configuración de rutas
DOCS_DIR = "docs"
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "http://localhost:5678/webhook-test/pregunta"
)
# EN TESTEO (NECESITA EJECUTAR WORKFLOW EN N8N)
#N8N_WEBHOOK_URL = "http://n8n:5678/webhook-test/pregunta"
#N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/pregunta"

def extraer_texto_de_archivo(ruta_completa, archivo):
    """Procesa un único archivo según su formato (PDF, TXT, MD, JSON) y devuelve su texto."""
    ext = archivo.lower()
    texto_archivo = ""
    
    try:
        # 1. Procesar PDFs
        if ext.endswith(".pdf"):
            reader = PdfReader(ruta_completa)
            texto_pdf = ""
            for page in reader.pages:
                texto_pdf += page.extract_text() + "\n"
            texto_archivo = f"--- CONTENIDO DEL ARCHIVO PDF ({archivo}) ---\n{texto_pdf}\n"
            print(f" PDF Procesado de forma individual: {archivo}")
            
        # 2. Procesar Texto Plano (TXT y MD)
        elif ext.endswith(".txt") or ext.endswith(".md"):
            with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                texto_plano = f.read()
            texto_archivo = f"--- CONTENIDO DEL ARCHIVO TEXTO ({archivo}) ---\n{texto_plano}\n"
            print(f" Texto/MD Procesado de forma individual: {archivo}")
            
        # 3. Procesar JSON
        elif ext.endswith(".json"):
            with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
                datos_json = json.load(f)
            texto_json = json.dumps(datos_json, indent=2, ensure_ascii=False)
            texto_archivo = f"--- CONTENIDO DEL ARCHIVO JSON ({archivo}) ---\n{texto_json}\n"
            print(f" JSON Procesado de forma individual: {archivo}")
            
        return texto_archivo

    except Exception as e:
        print(f" Error leyendo el archivo {archivo}: {str(e)}")
        return ""


def extraer_contexto_inteligente(directorio, pregunta, max_caracteres=3500):
    """
    Escanea la carpeta, puntúa de manera individual cada documento según las palabras 
    de la consulta y junta los resultados priorizando el archivo con mayor relevancia.
    """
    if not os.path.exists(directorio):
        return ""

    # Limpieza de conectores
    conectores = ["por", "que", "del", "con", "los", "las", "para", "una", "uno", "este", "como", "esta", "estos"]
    palabras_pregunta = [
        w.strip("?,.¿!").lower() 
        for w in pregunta.split() 
        if len(w) > 2 and w.lower() not in conectores
    ]
    if not palabras_pregunta:
        palabras_pregunta = [pregunta.lower()]

    archivos_puntuados = []

    # 1. Lectura y asignación de Scoring
    for archivo in os.listdir(directorio):
        ruta_completa = os.path.join(directorio, archivo)
        
        if os.path.isfile(ruta_completa):
            contenido_texto = extraer_texto_de_archivo(ruta_completa, archivo)
            if not contenido_texto.strip():
                continue
            
            # Contamos cuántas veces se repiten los conceptos clave en el texto total del archivo
            contenido_lower = contenido_texto.lower()
            puntaje = sum(contenido_lower.count(palabra) for palabra in palabras_pregunta)
            
            archivos_puntuados.append({
                "nombre": archivo,
                "texto": contenido_texto,
                "puntaje": puntaje
            })

    if not archivos_puntuados:
        return ""

    # Puntaje de archivos
    archivos_puntuados.sort(key=lambda x: x["puntaje"], reverse=True)

    # 3. Empaquetado del contexto acotado para evitar que n8n o la API tiren Timeout
    contexto_final = []
    caracteres_actuales = 0

    for item in archivos_puntuados:
        # Si el documento no tiene coincidencias y ya procesamos otros mejores, lo omitimos para ahorrar tokens
        if item["puntaje"] == 0 and len(contexto_final) > 0:
            continue
            
        texto_bloque = item["texto"] + "\n"
        
        if caracteres_actuales + len(texto_bloque) <= max_caracteres:
            contexto_final.append(texto_bloque)
            caracteres_actuales += len(texto_bloque)
        else:
            # Si se pasa del límite, cortamos el sobrante del archivo que corresponda
            espacio_libre = max_caracteres - caracteres_actuales
            if espacio_libre > 150:
                contexto_final.append(texto_bloque[:espacio_libre])
            break

    return "\n".join(contexto_final)


@app.post("/buscar")
async def buscar_contexto(consulta: Consulta):
    
    # 1. Validación de input vacío
    if not consulta.pregunta or not consulta.pregunta.strip():
        return {"output": "Error: Por favor, ingresa una consulta válida. No se admiten campos vacíos."}
        
    # 2. Validación de longitud máxima
    if len(consulta.pregunta) > 500:
        return {"output": "Error: La consulta es demasiado larga. Máximo 500 caracteres."}
        
    # 3. Validación anti-manipulación (Prompt Injection)
    PALABRAS_SOSPECHOSAS = ["ignora las instrucciones", "ignore previous instructions", "system prompt"]
    if any(frase in consulta.pregunta.lower() for frase in PALABRAS_SOSPECHOSAS):
        return {"output": "Error: Consulta rechazada por políticas de seguridad."}

    # Procesamiento final de RAG
    try:
        # Ingesta filtrada y ordenada milimétricamente usando Scoring
        contexto_perfecto = extraer_contexto_inteligente(DOCS_DIR, consulta.pregunta)
        
        if not contexto_perfecto or not contexto_perfecto.strip():
            return {"output": "Error: Base de conocimientos no disponible o vacía. Contacte al administrador."}
        
        # Generamos el payload optimizado hacia n8n
        payload = {
            "pregunta": consulta.pregunta,
            "contexto": contexto_perfecto
        }
        
        headers = {"Content-Type": "application/json; charset=utf-8"}
        
        # Mantenemos un margen de respuesta de 60s
        respuesta_n8n = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=60)
        datos_n8n = respuesta_n8n.json()
        
        # Esto se uso para probarlo en postman
        respuesta_para_postman = {
            "contexto_utilizado": contexto_perfecto
        }
        
        # Adaptamos la lectura del JSON según si n8n retorna un objeto plano o metido en listas
        if isinstance(datos_n8n, dict) and "output" in datos_n8n:
            respuesta_para_postman["output"] = datos_n8n["output"]
        elif isinstance(datos_n8n, list) and len(datos_n8n) > 0 and "output" in datos_n8n[0]:
            respuesta_para_postman["output"] = datos_n8n[0]["output"]
        else:
            respuesta_para_postman["output"] = "Aviso: Ejecutar Workflow en n8n"
            respuesta_para_postman["respuesta_cruda_n8n"] = datos_n8n

        return respuesta_para_postman
        
    except Exception as e:
        return {"output": f"Error en el procesamiento del sistema: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)