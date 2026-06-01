# Prueba Técnica – Martín Simón

Asistente automatizado de Soporte Técnico (Nivel 3) para MineCatalog.

La solución implementa un pipeline híbrido basado en:

- **FastAPI (Python)** para el procesamiento RAG y exposición de la API.
- **n8n** como orquestador de los flujos de IA.
- **OpenAI** para la generación de respuestas.
- **Docker Compose** para ejecutar todo el entorno de forma reproducible.

---

# Arquitectura

```text
Usuario
   │
   ▼
FastAPI (RAG)
   │
   ▼
n8n Workflow
   │
   ▼
OpenAI
   │
   ▼
Respuesta final
```

## Flujo de procesamiento

1. El usuario envía una consulta al backend.
2. FastAPI recupera el contexto relevante desde la documentación disponible.
3. El contexto y la pregunta se envían al workflow de n8n.
4. n8n utiliza OpenAI para generar la respuesta.
5. La respuesta es devuelta al usuario.

---

# Requisitos

- Docker
- Docker Compose

No se encuentra soportada la ejecución manual de los componentes fuera de Docker.

---

# Configuración

## Variables de entorno

Crear el archivo `.env` a partir del ejemplo:

```bash
cp .env.example .env
```

Configurar:

```env
N8N_WEBHOOK_URL=http://n8n:5678/webhook-test/pregunta
```

## OpenAI

La API Key de OpenAI se configura directamente dentro de n8n mediante la credencial correspondiente.

Por razones de seguridad, la clave no forma parte del código fuente ni del archivo `.env`.

---

# Despliegue

Desde la raíz del proyecto ejecutar:

```bash
docker compose up --build
```

Esto iniciará:

- Backend FastAPI
- Instancia de n8n
- Red interna de comunicación entre servicios
# En caso de Error por servicios activos ejecutar previamente
```bash
docker rm -f minecatalog_backend
docker rm -f n8n
```
---

# Configuración de n8n

1. Abrir:

```text
http://localhost:5678
```

2. Crear un usuario administrador.
3. Seleccionar **Import from File**.
4. Importar `workflow_n8n.json`.
5. Configurar la credencial de OpenAI en su nodo correspondiente.
6. Ejecutar el workflow utilizando **Execute Workflow**.

---

# Uso

## Consulta desde consola

```bash
python3 chat.py
```

## Consulta mediante API / POSTMAN para ver contexto enviado

### Endpoint

```http
POST http://localhost:8000/buscar
```

### Body

```json
{
  "pregunta": "Hola! tengo esto: Error: código de material duplicado"
}
```

---

# Pruebas Automatizadas

Ejecutar:

```bash
docker exec minecatalog_backend pytest test_main.py
```

---

# Manejo de Errores

El sistema contempla los siguientes escenarios:

### Preguntas sin respuesta

Si no existe información suficiente en la documentación cargada, el sistema devuelve una respuesta indicando que no se encontró información relevante para responder la consulta.


### Timeouts

Las solicitudes externas poseen límites de tiempo de espera configurados para evitar bloqueos indefinidos del servicio.

### Entradas vacías

Si el usuario envía una consulta vacía o inválida, el backend responde con un error de validación apropiado.

---

# Estructura del Proyecto

```text
.
├── main.py
├── chat.py
├── workflow_n8n.json
├── requirements.txt
├── test_main.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
└── Docs/
    ├── Documentación 1.pdf
    ├── Documentación 2.txt
    ├── Documentación 3.md
    └── Documentación 4.json
```

---

# Decisiones de Diseño

### FastAPI

Se utilizó FastAPI para exponer una API REST simple y eficiente, permitiendo desacoplar la lógica de recuperación de contexto del procesamiento realizado por el modelo de lenguaje.

### n8n

Se eligió n8n como orquestador para centralizar el flujo de IA, facilitando futuras extensiones, integración con otros servicios y modificaciones del workflow sin afectar el backend.

### Docker

Toda la solución se ejecuta mediante Docker Compose para garantizar reproducibilidad, simplificar el despliegue y evitar diferencias entre entornos de desarrollo y evaluación.

### Arquitectura RAG

La arquitectura Retrieval-Augmented Generation (RAG) permite complementar las respuestas generadas por el modelo con información proveniente de la documentación suministrada, reduciendo alucinaciones y mejorando la precisión de las respuestas.