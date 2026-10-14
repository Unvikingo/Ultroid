
import re
from datetime import datetime, timezone

from telethon.tl.types import (
    User,
    MessageMediaGeo,
    MessageMediaGeoLive,
    MessageMediaVenue
)
from telethon.tl.functions.contacts import (
    ResolveUsernameRequest
)
from telethon.tl.functions.users import (
    GetFullUserRequest
)
from telethon.errors import RPCError


def nombre_usuario(usuario):
    return " ".join(filter(None, [
        usuario.first_name,
        usuario.last_name
    ])) or "Sin nombre visible"


def username_usuario(usuario):
    username = getattr(usuario, "username", None)
    return f"@{username}" if username else "Sin username público"


async def resolver_usuario(event, argumento):
    cliente = event.client

    if not argumento:
        respuesta = await event.get_reply_message()

        if respuesta:
            remitente = await respuesta.get_sender()
            if remitente:
                return remitente

        return await cliente.get_me()

    texto = argumento.strip()

    enlace = re.match(
        r"^https?://(?:www\.)?t\.me/([^/?#]+)",
        texto,
        re.IGNORECASE
    )

    if enlace:
        texto = enlace.group(1)

    if texto.lstrip("-").isdigit():
        return await cliente.get_entity(int(texto))

    username = texto.lstrip("@")

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{4,31}",
        username
    ):
        raise ValueError("Formato de usuario inválido")

    resultado = await cliente(
        ResolveUsernameRequest(username)
    )

    for usuario in resultado.users:
        actual = (
            getattr(usuario, "username", None)
            or ""
        )

        if actual.lower() == username.lower():
            return usuario

    return None


async def obtener_bio(event, usuario):
    try:
        resultado = await event.client(
            GetFullUserRequest(usuario)
        )

        return (
            resultado.full_user.about
            or "Sin biografía pública"
        )

    except RPCError:
        return "No accesible en esta consulta"


def leer_ubicacion(mensaje):
    if not mensaje:
        return None

    media = getattr(mensaje, "media", None)

    if not isinstance(media, (
        MessageMediaGeo,
        MessageMediaGeoLive,
        MessageMediaVenue
    )):
        return None

    geo = getattr(media, "geo", None)

    if geo is None:
        return None

    latitud = getattr(geo, "lat", None)
    longitud = getattr(geo, "long", None)

    if latitud is None or longitud is None:
        return None

    resultado = {
        "lat": latitud,
        "lon": longitud,
        "tipo": "Ubicación compartida",
        "lugar": None,
        "direccion": None,
        "fecha": getattr(mensaje, "date", None),
        "estado": "Punto compartido; actualidad no verificada"
    }

    if isinstance(media, MessageMediaVenue):
        resultado["tipo"] = "Lugar compartido"
        resultado["lugar"] = getattr(
            media, "title", None
        )
        resultado["direccion"] = getattr(
            media, "address", None
        )

    elif isinstance(media, MessageMediaGeoLive):
        resultado["tipo"] = "Ubicación en vivo"

        periodo = getattr(
            media, "period", None
        )

        inicio = getattr(
            mensaje, "date", None
        )

        if periodo and inicio:
            ahora = datetime.now(timezone.utc)

            transcurrido = (
                ahora - inicio
            ).total_seconds()

            if transcurrido >= periodo:
                resultado["estado"] = (
                    "Período de publicación finalizado"
                )
            else:
                resultado["estado"] = (
                    "Dentro del período de publicación; "
                    "posición actual no verificada"
                )

    return resultado


def fecha_legible(fecha):
    if not fecha:
        return "No disponible"

    return fecha.strftime("%d/%m/%Y %H:%M UTC")


def texto_ubicacion(ubicacion):
    if not ubicacion:
        return (
            "📍 UBICACIÓN COMPARTIDA\n"
            "No se encontró una ubicación adjunta "
            "al mensaje consultado.\n\n"
            "Un ID o username no revela "
            "coordenadas GPS."
        )

    lat = ubicacion["lat"]
    lon = ubicacion["lon"]

    texto = (
        "📍 UBICACIÓN COMPARTIDA\n"
        f"Tipo: {ubicacion['tipo']}\n"
        f"Latitud: {lat}\n"
        f"Longitud: {lon}\n"
        f"Fecha del mensaje: "
        f"{fecha_legible(ubicacion['fecha'])}\n"
        f"Estado: {ubicacion['estado']}\n"
    )

    if ubicacion["lugar"]:
        texto += (
            f"Lugar: {ubicacion['lugar'][:100]}\n"
        )

    if ubicacion["direccion"]:
        texto += (
            "Dirección publicada: "
            f"{ubicacion['direccion'][:150]}\n"
        )

    texto += (
        "\n🗺️ MAPA\n"
        f"https://www.google.com/maps?q={lat},{lon}"
    )

    return texto


@ultroid_cmd(pattern=r"ubicacion2(?:\s+(.+))?$")
async def ubicacion_suprema_v2(event):
    argumento = event.pattern_match.group(1)

    try:
        usuario = await resolver_usuario(
            event, argumento
        )

        if not isinstance(usuario, User):
            return await event.eor(
                "❌ No se encontró una cuenta "
                "personal o bot accesible."
            )

        bio = await obtener_bio(
            event, usuario
        )

        respuesta = await event.get_reply_message()
        ubicacion = None

        if respuesta:
            remitente = await respuesta.get_sender()

            if (
                remitente
                and remitente.id == usuario.id
            ):
                ubicacion = leer_ubicacion(
                    respuesta
                )

        ficha = (
            "👑 UBICACIÓN SUPREMA V2 👑\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"

            "👤 IDENTIDAD PÚBLICA\n"
            f"Nombre: {nombre_usuario(usuario)[:80]}\n"
            f"ID: {usuario.id}\n"
            f"Username: {username_usuario(usuario)}\n"
            f"Tipo: {'Bot' if usuario.bot else 'Usuario'}\n\n"

            "🌎 INFORMACIÓN DECLARADA\n"
            f"Biografía: {bio[:500]}\n\n"

            f"{texto_ubicacion(ubicacion)}\n\n"

            "🏙️ CIUDAD Y PAÍS\n"
            "No verificados automáticamente.\n"
            "Pueden aparecer en la descripción "
            "de un lugar compartido.\n\n"

            "🔐 PRIVACIDAD\n"
            "GPS privado: No accesible\n"
            "IP del usuario: No accesible\n"
            "Ubicación por ID: No accesible\n"
            "Ubicación por username: No accesible\n\n"

            "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
        )

        await event.eor(ficha[:4000])

    except ValueError:
        await event.eor(
            "❌ Username o ID inválido "
            "o no accesible para tu cuenta."
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
