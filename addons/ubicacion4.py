
import re
from telethon.tl.types import (
    User,
    MessageMediaGeo,
    MessageMediaGeoLive,
    MessageMediaVenue,
    MessageMediaPhoto,
    MessageMediaDocument
)
from telethon.tl.functions.contacts import (
    ResolveUsernameRequest
)
from telethon.tl.functions.users import (
    GetFullUserRequest
)
from telethon.errors import RPCError


def nombre_de(usuario):
    return " ".join(filter(None, [
        usuario.first_name,
        usuario.last_name
    ])) or "Sin nombre visible"


async def resolver(event, argumento):
    if not argumento:
        mensaje = await event.get_reply_message()

        if mensaje:
            remitente = await mensaje.get_sender()
            if remitente:
                return remitente

        return await event.client.get_me()

    texto = argumento.strip()

    enlace = re.match(
        r"^https?://(?:www\.)?t\.me/([^/?#]+)",
        texto,
        re.IGNORECASE
    )

    if enlace:
        texto = enlace.group(1)

    if texto.lstrip("-").isdigit():
        return await event.client.get_entity(
            int(texto)
        )

    username = texto.lstrip("@")

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{4,31}",
        username
    ):
        raise ValueError("Username inválido")

    resultado = await event.client(
        ResolveUsernameRequest(username)
    )

    for usuario in resultado.users:
        if (
            (usuario.username or "").lower()
            == username.lower()
        ):
            return usuario

    return None


async def consultar_bio(event, usuario):
    try:
        completo = await event.client(
            GetFullUserRequest(usuario)
        )

        return (
            completo.full_user.about
            or "Sin biografía publicada"
        )

    except RPCError:
        return "Biografía no accesible"


def analizar_mensaje(mensaje):
    if not mensaje:
        return {
            "tipo": "Sin mensaje respondido",
            "ubicacion": None
        }

    media = getattr(mensaje, "media", None)

    if isinstance(media, (
        MessageMediaGeo,
        MessageMediaGeoLive,
        MessageMediaVenue
    )):
        geo = getattr(media, "geo", None)

        if geo:
            lat = getattr(geo, "lat", None)
            lon = getattr(geo, "long", None)

            if lat is not None and lon is not None:
                if isinstance(
                    media, MessageMediaGeoLive
                ):
                    tipo = "Ubicación en vivo compartida"

                elif isinstance(
                    media, MessageMediaVenue
                ):
                    tipo = "Lugar compartido"

                else:
                    tipo = "Ubicación compartida"

                return {
                    "tipo": tipo,
                    "ubicacion": {
                        "lat": lat,
                        "lon": lon,
                        "lugar": getattr(
                            media, "title", None
                        ),
                        "direccion": getattr(
                            media, "address", None
                        ),
                        "fecha": getattr(
                            mensaje, "date", None
                        )
                    }
                }

    if isinstance(media, MessageMediaPhoto):
        tipo = "Fotografía"

    elif isinstance(media, MessageMediaDocument):
        documento = getattr(
            media, "document", None
        )

        mime = getattr(
            documento, "mime_type", ""
        ) or ""

        if mime.startswith("video/"):
            tipo = "Video"
        elif mime.startswith("image/"):
            tipo = "Imagen o archivo"
        else:
            tipo = "Documento"

    elif getattr(mensaje, "message", None):
        tipo = "Mensaje de texto"

    else:
        tipo = "Otro tipo de mensaje"

    return {
        "tipo": tipo,
        "ubicacion": None
    }


def describir_ubicacion(datos):
    ubicacion = datos["ubicacion"]

    if not ubicacion:
        return (
            "📍 UBICACIÓN\n"
            "El mensaje no contiene una "
            "ubicación de Telegram.\n"
            "GPS: No disponible\n"
            "Ciudad: No verificada\n"
            "País: No verificado\n\n"
            "Un texto, foto o video no "
            "proporciona automáticamente "
            "el GPS del autor."
        )

    lat = ubicacion["lat"]
    lon = ubicacion["lon"]

    fecha = ubicacion["fecha"]

    fecha_texto = (
        fecha.strftime("%d/%m/%Y %H:%M UTC")
        if fecha
        else "No disponible"
    )

    texto = (
        "📍 UBICACIÓN COMPARTIDA\n"
        f"Latitud: {lat}\n"
        f"Longitud: {lon}\n"
        f"Fecha del mensaje: {fecha_texto}\n"
    )

    if ubicacion["lugar"]:
        texto += (
            "Lugar: "
            + ubicacion["lugar"][:100]
            + "\n"
        )

    if ubicacion["direccion"]:
        texto += (
            "Dirección publicada: "
            + ubicacion["direccion"][:150]
            + "\n"
        )

    texto += (
        "\n🗺️ GOOGLE MAPS\n"
        f"https://www.google.com/maps?q={lat},{lon}\n\n"
        "Ciudad y país: Consultables en el mapa.\n"
        "La ubicación puede ser antigua "
        "o corresponder a un lugar elegido, "
        "no necesariamente a la posición "
        "actual del usuario."
    )

    return texto


@ultroid_cmd(pattern=r"ubicacion4(?:\s+(.+))?$")
async def ubicacion_suprema_v4(event):
    argumento = event.pattern_match.group(1)

    try:
        usuario = await resolver(
            event, argumento
        )

        if not isinstance(usuario, User):
            return await event.eor(
                "❌ No se encontró un usuario "
                "accesible. Este comando "
                "analiza cuentas personales y bots."
            )

        bio = await consultar_bio(
            event, usuario
        )

        respuesta = await event.get_reply_message()

        # Evita atribuir la ubicación
        # de un mensaje a otra persona.
        if respuesta:
            remitente = await respuesta.get_sender()

            if (
                remitente
                and remitente.id == usuario.id
            ):
                analisis = analizar_mensaje(
                    respuesta
                )
            else:
                analisis = {
                    "tipo": (
                        "El mensaje respondido "
                        "no pertenece al objetivo"
                    ),
                    "ubicacion": None
                }
        else:
            analisis = analizar_mensaje(None)

        username = (
            f"@{usuario.username}"
            if usuario.username
            else "Sin username público"
        )

        ficha = (
            "👑 UBICACIÓN SUPREMA V4 👑\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"

            "👤 IDENTIDAD PÚBLICA\n"
            f"Nombre: {nombre_de(usuario)[:80]}\n"
            f"ID: {usuario.id}\n"
            f"Username: {username}\n"
            f"Tipo: {'Bot' if usuario.bot else 'Usuario'}\n\n"

            "📝 BIOGRAFÍA\n"
            f"{bio[:400]}\n\n"

            "🔎 ANÁLISIS DEL MENSAJE\n"
            f"Tipo: {analisis['tipo']}\n\n"

            f"{describir_ubicacion(analisis)}\n\n"

            "🔐 PRIVACIDAD\n"
            "GPS privado: No accesible\n"
            "IP privada: No accesible\n"
            "Localización por ID: No disponible\n"
            "Localización por username: No disponible\n\n"

            "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
        )

        await event.eor(ficha[:4000])

    except ValueError:
        await event.eor(
            "❌ ID o username inválido "
            "o no accesible."
        )

    except RPCError as error:
        await event.eor(
            "❌ Error de Telegram: "
            + type(error).__name__
        )

    except Exception as error:
        await event.eor(
            "❌ Error del addon: "
            + type(error).__name__
        )
