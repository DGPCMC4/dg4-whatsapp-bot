"""
Motor de interpretación de preguntas del chatbot de consulta.

No usa IA externa ni internet: combina coincidencia difusa (RapidFuzz) para
encontrar la institución, con un mapeo de palabras clave para identificar
qué campo(s) se están pidiendo (teléfono, correo, enlace, etc.).
"""
from rapidfuzz import fuzz, process

# Palabras clave -> campo de la base de datos.
# El orden importa poco; se revisan todas y se acumulan coincidencias.
PALABRAS_CLAVE_CAMPO = {
    "telefono": ["telefono", "teléfono", "tel", "numero", "número"],
    "extension": ["extension", "extensión", "ext"],
    "whatsapp": ["whatsapp", "whats app", "wasap"],
    "correo": ["correo", "email", "e-mail", "mail", "correo electronico", "correo electrónico"],
    "enlace_nombre": ["enlace", "contacto", "responsable", "quien es", "quién es", "nombre del enlace"],
    "enlace_cargo": ["cargo", "puesto"],
    "direccion": ["direccion", "dirección", "domicilio", "ubicacion", "ubicación"],
    "horario_atencion": ["horario", "horarios", "atencion", "atención"],
    "ramo": ["ramo"],
}

# Nombres amigables para armar la respuesta
ETIQUETAS_CAMPO = {
    "telefono": "Teléfono",
    "extension": "Extensión",
    "whatsapp": "WhatsApp",
    "correo": "Correo electrónico",
    "enlace_nombre": "Enlace",
    "enlace_cargo": "Cargo del enlace",
    "direccion": "Dirección",
    "horario_atencion": "Horario de atención",
    "ramo": "Ramo",
}

CAMPOS_COMPLETOS = list(ETIQUETAS_CAMPO.keys())

# Palabras que no aportan a identificar la institución (se quitan antes de buscar coincidencia)
PALABRAS_VACIAS = {
    "el", "la", "los", "las", "de", "del", "al", "a", "que", "es", "son", "y", "o",
    "para", "por", "con", "dame", "dime", "me", "puedes", "podrias", "podrías",
    "cual", "cuál", "cuales", "cuáles", "quien", "quién", "quienes", "quiénes",
    "sabes", "necesito", "quiero", "favor", "porfavor", "datos", "dato", "completos",
    "completo", "ficha", "informacion", "información", "sobre", "tiene", "tienes",
}
PALABRAS_VACIAS |= {p for claves in PALABRAS_CLAVE_CAMPO.values() for clave in claves for p in clave.split()}


def _texto_institucion(pregunta: str) -> str:
    """Quita palabras clave de campo y palabras vacías, dejando (idealmente) solo
    el nombre/siglas de la institución para comparar."""
    palabras = [p.strip("¿?.,;:!") for p in pregunta.lower().split()]
    utiles = [p for p in palabras if p and p not in PALABRAS_VACIAS]
    return " ".join(utiles) if utiles else pregunta.lower()


def detectar_campos_pedidos(pregunta: str) -> list[str]:
    """Devuelve la lista de campos que el usuario parece estar pidiendo.
    Si no detecta ninguno en particular, se asume que quiere la ficha completa."""
    texto = pregunta.lower()
    encontrados = []
    for campo, claves in PALABRAS_CLAVE_CAMPO.items():
        if any(clave in texto for clave in claves):
            encontrados.append(campo)

    if not encontrados:
        return CAMPOS_COMPLETOS

    # Teléfono y extensión se muestran siempre juntos: una conmutadora sin
    # extensión rara vez sirve de algo en una dependencia de gobierno.
    if "telefono" in encontrados and "extension" not in encontrados:
        encontrados.append("extension")
    elif "extension" in encontrados and "telefono" not in encontrados:
        encontrados.insert(0, "telefono")

    return encontrados


def encontrar_institucion(pregunta: str, instituciones: list[dict], umbral: int = 72):
    """
    Busca, entre las instituciones cargadas, la(s) que mejor coincidan con el
    texto de la pregunta, comparando contra 'entidad' y 'siglas'.
    Devuelve una lista ordenada de tuplas (score, institucion), mejor primero.
    """
    texto_completo = pregunta.lower()
    texto_limpio = _texto_institucion(pregunta)
    palabras_pregunta = {p.strip(".,;:¿?") for p in texto_completo.split()}

    candidatos = {}
    for inst in instituciones:
        entidad = (inst.get("entidad") or "").lower()
        siglas = (inst.get("siglas") or "").lower()

        # token_set_ratio compara conjuntos de palabras: tolera texto de más
        # (preguntas largas) sin premiar coincidencias parciales de sub-palabras.
        score_entidad = fuzz.token_set_ratio(texto_limpio, entidad) if entidad else 0
        score_siglas = fuzz.ratio(texto_limpio, siglas) if siglas else 0

        # Coincidencia exacta de siglas como palabra suelta pesa al máximo (ej. "SADER")
        if siglas and siglas in palabras_pregunta:
            score_siglas = 100

        score = max(score_entidad, score_siglas)
        if score >= umbral:
            candidatos[inst["id"]] = (score, inst)

    resultados = sorted(candidatos.values(), key=lambda x: x[0], reverse=True)
    return resultados  # lista de tuplas (score, institucion)


def responder_consulta(pregunta: str, instituciones: list[dict], institucion_contexto: dict | None = None) -> dict:
    """
    Punto de entrada del chatbot de consulta.
    'institucion_contexto' es la última institución de la que se habló en esta
    conversación (la manda el frontend); permite responder preguntas de
    seguimiento como "y la extensión" o "y su correo" sin repetir el nombre.
    Devuelve un dict con: tipo ('ok' | 'ambiguo' | 'no_encontrado'), y los datos
    necesarios para que el frontend construya la respuesta conversacional.
    """
    coincidencias = encontrar_institucion(pregunta, instituciones)
    campos = detectar_campos_pedidos(pregunta)

    if not coincidencias:
        # Sin ninguna institución mencionada: si la pregunta trae una palabra clave
        # de campo (teléfono, correo, etc.) y hay contexto de la institución anterior,
        # se asume que sigue preguntando por esa misma institución.
        campos_explicitos = campos != CAMPOS_COMPLETOS
        if institucion_contexto and campos_explicitos:
            return {
                "tipo": "ok",
                "institucion": institucion_contexto,
                "campos": campos,
                "etiquetas": ETIQUETAS_CAMPO,
                "por_contexto": True,
            }
        return {"tipo": "no_encontrado", "pregunta": pregunta}

    mejor_score, mejor_inst = coincidencias[0]

    # Solo se pregunta "¿cuál de estas?" si hay otra coincidencia casi tan buena
    # como la mejor (diferencia menor a 12 puntos). Si la mejor destaca claramente,
    # se usa directo aunque existan otras coincidencias débiles.
    reñidas = [inst for score, inst in coincidencias[:5] if (mejor_score - score) < 12]

    if len(reñidas) > 1:
        return {
            "tipo": "ambiguo",
            "pregunta": pregunta,
            "opciones": [{"id": i["id"], "entidad": i["entidad"], "siglas": i["siglas"]} for i in reñidas],
            "campos": campos,
        }

    return {
        "tipo": "ok",
        "institucion": mejor_inst,
        "campos": campos,
        "etiquetas": ETIQUETAS_CAMPO,
    }
