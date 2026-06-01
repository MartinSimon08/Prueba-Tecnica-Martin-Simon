import requests
import os
from dotenv import load_dotenv


load_dotenv()
URL_FASTAPI = os.getenv("BACKEND_URL", "http://localhost:8000/buscar")

print("SISTEMA DE PRUEBA DE CONSOLA - MINECATALOG")
print("Escriba su consulta y presione Enter. Para finalizar, escriba 'salir'.")


while True:
    try:
        # Captura la entrada del usuario de forma segura
        pregunta = input("Consulta: ")
    except (KeyboardInterrupt, EOFError):
        print("\nSesión finalizada.")
        break
    
    # Condición de salida
    if pregunta.lower().strip() == "salir":
        print("Sesión de consola finalizada.")
        break
        
    # Validación local 1: Evitar inputs vacíos antes de enviar
    if not pregunta.strip():
        print("Aviso: No se admiten consultas vacías.\n")
        continue

    # Validación local 2: Controlar los 500 caracteres antes de pegarle a FastAPI
    if len(pregunta) > 500:
        print(f"Error local: La consulta es demasiado larga ({len(pregunta)} caracteres). Máximo permitido: 500.\n")
        continue

    print("Procesando solicitud...")
    
    try:
        payload = {"pregunta": pregunta}
        respuesta = requests.post(URL_FASTAPI, json=payload, timeout=60)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            
            print("\nRespuesta del Sistema:")
            # Muestra el output de la IA o el mensaje de error que devuelva FastAPI
            print(datos.get("output", "No se recibió respuesta del servidor."))
            print("-" * 60 + "\n")
        else:
            print(f"Error de servidor: Código de estado {respuesta.status_code}\n")
            
    except Exception as e:
        print(f"Error de conexión: No se pudo establecer comunicación con FastAPI. Detalle: {e}\n")