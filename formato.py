"""Convierte el resultado de search.responder_consulta() en texto plano para WhatsApp."""

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


def texto_ficha(institucion: dict, campos: list[str], por_contexto: bool = False) -> str:
    campos_mostrar = campos or list(ETIQUETAS_CAMPO.keys())
    lineas = []
    if por_contexto:
        lineas.append(f"_Sigo hablando de {institucion.get('siglas') or institucion['entidad']}_")

    nombre = institucion["entidad"]
    if institucion.get("siglas"):
        nombre += f" ({institucion['siglas']})"
    lineas.append(f"*{nombre}*")

    algun_dato = False
    for campo in campos_mostrar:
        valor = institucion.get(campo)
        if valor:
            algun_dato = True
            lineas.append(f"{ETIQUETAS_CAMPO.get(campo, campo)}: {valor}")

    if not algun_dato:
        lineas.append("Aún no hay datos de contacto capturados para esta institución.")

    return "\n".join(lineas)


def texto_ambiguo(opciones: list[dict]) -> str:
    lineas = ["Encontré varias instituciones parecidas. Responde con el número:"]
    for i, op in enumerate(opciones, start=1):
        nombre = op["entidad"]
        if op.get("siglas"):
            nombre += f" ({op['siglas']})"
        lineas.append(f"{i}. {nombre}")
    return "\n".join(lineas)


def texto_no_encontrado(pregunta: str) -> str:
    return (
        f'No encontré ninguna institución de la DG4 que coincida con "{pregunta}". '
        "Intenta con el nombre completo o las siglas (ej. teléfono de SADER)."
    )
