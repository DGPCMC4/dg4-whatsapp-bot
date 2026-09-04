"""
Funciones mínimas para enviar mensajes de texto vía la API de WhatsApp Cloud (Meta).
No usa ningún SDK de terceros, solo 'requests' (HTTP directo a la API oficial).
"""
import os

import requests

GRAPH_API_VERSION = "v21.0"


def _url_mensajes() -> str:
    phone_number_id = os.environ["PHONE_NUMBER_ID"]
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"


def enviar_texto(numero_destino: str, texto: str) -> dict:
    """Envía un mensaje de texto plano. 'numero_destino' debe incluir código de país, sin '+' ni espacios."""
    token = os.environ["WHATSAPP_ACCESS_TOKEN"]
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto[:4096]},  # WhatsApp limita el largo de un mensaje de texto
    }
    resp = requests.post(
        _url_mensajes(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    if resp.status_code >= 400:
        print(f"[whatsapp] Error al enviar mensaje a {numero_destino}: {resp.status_code} {resp.text}")
    return resp.json() if resp.content else {}
