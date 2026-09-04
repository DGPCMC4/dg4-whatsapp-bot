"""
Directorio DG4 - Mini-servicio de WhatsApp

Servicio independiente, pensado para desplegarse en la nube (Render) y así no
depender de que la PC de la DG4 esté encendida ni de exponerla a internet.

IMPORTANTE: por diseño, este servicio NO se conecta a data/dg4.db (esa base
vive solo en la red interna de la DG4). En su lugar, lee una COPIA exportada
de los datos de contacto (instituciones.json), que se actualiza con
scripts/exportar_instituciones_json.py y se sube a GitHub cada vez que haya
cambios importantes. Render vuelve a desplegar automáticamente al detectar el
cambio en el repositorio.

Arranca localmente con: python whatsapp/bot.py
En Render, el comando de arranque es: uvicorn bot:app --host 0.0.0.0 --port $PORT
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

import formato
import meta_api
import search  # copia local de backend/search.py (ver nota en LEEME_WHATSAPP.md)

load_dotenv(Path(__file__).parent / ".env")  # en Render, las variables se configuran en su panel, no con .env

DATOS_PATH = Path(__file__).parent / "instituciones.json"
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

app = FastAPI(title="Directorio DG4 - WhatsApp")

# Contexto de conversación por número de teléfono (en memoria; se reinicia si
# el servicio se reinicia, lo cual es aceptable para el piloto de prueba).
CONTEXTO_POR_NUMERO: dict[str, dict] = {}


def cargar_instituciones() -> list[dict]:
    with open(DATOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_institucion(institucion_id: int, instituciones: list[dict]) -> dict | None:
    for inst in instituciones:
        if inst["id"] == institucion_id:
            return inst
    return None


def procesar_mensaje(numero: str, texto: str, instituciones: list[dict]) -> str:
    estado = CONTEXTO_POR_NUMERO.setdefault(numero, {})
    texto = texto.strip()

    # Si le habíamos preguntado "¿cuál de estas?" y responde solo un número,
    # resolvemos la ambigüedad directamente sin volver a buscar.
    pendientes = estado.get("opciones_pendientes")
    if pendientes and texto.isdigit():
        idx = int(texto) - 1
        if 0 <= idx < len(pendientes):
            institucion = obtener_institucion(pendientes[idx]["id"], instituciones)
            estado["ultima_institucion_id"] = institucion["id"]
            estado.pop("opciones_pendientes", None)
            campos = estado.pop("campos_pendientes", None)
            return formato.texto_ficha(institucion, campos)
        return "Ese número no está en la lista. Intenta de nuevo."

    institucion_contexto = None
    if estado.get("ultima_institucion_id"):
        institucion_contexto = obtener_institucion(estado["ultima_institucion_id"], instituciones)

    resultado = search.responder_consulta(texto, instituciones, institucion_contexto)

    if resultado["tipo"] == "ok":
        estado["ultima_institucion_id"] = resultado["institucion"]["id"]
        estado.pop("opciones_pendientes", None)
        return formato.texto_ficha(resultado["institucion"], resultado["campos"], resultado.get("por_contexto", False))

    if resultado["tipo"] == "ambiguo":
        estado["opciones_pendientes"] = resultado["opciones"]
        estado["campos_pendientes"] = resultado["campos"]
        return formato.texto_ambiguo(resultado["opciones"])

    return formato.texto_no_encontrado(resultado["pregunta"])


@app.get("/webhook")
def verificar_webhook(request: Request):
    """Meta llama a esto una sola vez, al configurar el webhook, para confirmar que es tuyo."""
    modo = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if modo == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def recibir_mensaje(request: Request):
    """Meta llama a esto cada vez que alguien le escribe al número de WhatsApp."""
    datos = await request.json()

    try:
        instituciones = cargar_instituciones()
        entradas = datos.get("entry", [])
        for entrada in entradas:
            for cambio in entrada.get("changes", []):
                valor = cambio.get("value", {})
                for mensaje in valor.get("messages", []):
                    if mensaje.get("type") != "text":
                        continue  # por ahora solo atendemos mensajes de texto
                    numero = mensaje["from"]
                    texto = mensaje["text"]["body"]
                    respuesta = procesar_mensaje(numero, texto, instituciones)
                    meta_api.enviar_texto(numero, respuesta)
    except Exception as e:
        print(f"[whatsapp] Error procesando webhook: {e}")

    # WhatsApp espera un 200 rápido, sin importar el contenido.
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    if not VERIFY_TOKEN or not os.environ.get("WHATSAPP_ACCESS_TOKEN"):
        print("\n*** Falta configurar whatsapp/.env (copia .env.example y llénalo) ***\n")

    print("\nMini-servicio de WhatsApp escuchando en: http://localhost:8001/webhook\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)
