
import asyncio
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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


def nombre_de(usuario):
    return " ".join(filter(None, [
        usuario.first_name,
        usuario.last_name
    ])) or "Sin nombre visible"


async def resolver_usuario(event, texto):
    if not texto:
        respuesta = await event.get_reply_message()

        if respuesta:
            remitente = await respuesta.get_sender()
            if remitente:
                return remitente

        return await event.client.get_me()

    texto = texto.strip()

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
        return "No accesible"


def extraer_ubicacion(mensaje):
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

    lat = getattr(geo, "lat", None)
    lon = getattr(geo, "long", None)

    if lat is None or lon is None:
        return None

    tipo = "Ubicación compartida"

    if isinstance(media, MessageMediaGeoLive):
        tipo = "Ubicación en vivo compartida"

    elif isinstance(media, MessageMediaVenue):
        tipo = "Lugar compartido"

    return {
        "lat": lat,
        "lon": lon,
        "tipo": tipo,
        "fecha": getattr(mensaje, "date", None),
        "lugar": getattr(media, "title", None),
        "direccion": getattr(media, "address", None)
    }


def consultar_nominatim(lat, lon):
    parametros = urlencode({
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 10
    })

    url = (
        "https://nominatim.openstreetmap.org/"
        "reverse?" + parametros
    )

    solicitud = Request(
        url,
        headers={
            "User-Agent": (
                "UltroidValhallaLocation/1.0 "
                "(personal Telegram addon)"
            ),
            "Accept": "application/json"
        }
    )

    with urlopen(solicitud, timeout=8) as respuesta:
        datos = json.load(respuesta)

    direccion = datos.get("address", {})

    ciudad = (
        direccion.get("city")
        or direccion.get("town")
        or direccion.get("village")
        or direccion.get("municipality")
        or direccion.get("county")
        or "No identificada"
    )

    estado = (
        direccion.get("state")
        or direccion.get("region")
        or "No identificado"
    )

    pais = (
        direccion.get("country")
        or "No identificado"
    )

    return {
        "ciudad": ciudad,
        "estado": estado,
        "pais": pais
    }


async def geocodificar(lat, lon):
    try:
        return await asyncio.to_thread(
            consultar_nominatim,
            lat,
            lon
        )
    except Exception:
        return {
            "ciudad": "No identificada",
            "estado": "No identificado",
            "pais": "No identificado"
        }


@ultroid_cmd(pattern=r"ubicacion3(?:\s+(.+))?$")
async def ubicacion_suprema_v3(event):
    argumento = event.pattern_match.group(1)

    try:
        usuario = await resolver_usuario(
            event,
            argumento
        )

        if not isinstance(usuario, User):
            return await event.eor(
                "❌ No se encontró un usuario accesible."
            )

        bio = await obtener_bio(
            event,
            usuario
        )

        respuesta = await event.get_reply_message()
        ubicacion = None

        if respuesta:
            remitente = await respuesta.get_sender()

            if (
                remitente
                and remitente.id == usuario.id
            ):
                ubicacion = extraer_ubicacion(
                    respuesta
                )

        username = (
            f"@{usuario.username}"
            if usuario.username
            else "Sin username público"
        )

        ficha = (
            "👑 UBICACIÓN SUPREMA V3 👑\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"
            "👤 IDENTIDAD\n"
            f"Nombre: {nombre_de(usuario)[:80]}\n"
            f"ID: {usuario.id}\n"
            f"Username: {username}\n\n"
            "🌎 INFORMACIÓN DECLARADA\n"
            f"Biografía: {bio[:400]}\n\n"
        )

        if ubicacion:
            lat = ubicacion["lat"]
            lon = ubicacion["lon"]

            lugar = await geocodificar(
                lat,
                lon
            )

            fecha = ubicacion["fecha"]

            fecha_texto = (
                fecha.strftime("%d/%m/%Y %H:%M UTC")
                if fecha
                else "No disponible"
            )

            ficha += (
                "📍 UBICACIÓN COMPARTIDA\n"
                f"Tipo: {ubicacion['tipo']}\n"
                f"Latitud: {lat}\n"
                f"Longitud: {lon}\n"
                f"Fecha: {fecha_texto}\n\n"
                "🌍 REGIÓN IDENTIFICADA\n"
                f"Ciudad: {lugar['ciudad']}\n"
                f"Estado: {lugar['estado']}\n"
                f"País: {lugar['pais']}\n\n"
            )

            if ubicacion["lugar"]:
                ficha += (
                    "📌 Lugar publicado: "
                    f"{ubicacion['lugar'][:100]}\n"
                )

            if ubicacion["direccion"]:
                ficha += (
                    "🛣️ Dirección publicada: "
                    f"{ubicacion['direccion'][:120]}\n"
                )

            ficha += (
                "\n🗺️ GOOGLE MAPS\n"
                "https://www.google.com/maps"
                f"?q={lat},{lon}\n\n"
            )

        else:
            ficha += (
                "📍 UBICACIÓN\n"
                "No hay coordenadas compartidas "
                "en el mensaje consultado.\n\n"
                "🏙️ Ciudad: No verificada\n"
                "🌎 País: No verificado\n\n"
            )

        ficha += (
            "🔐 PRIVACIDAD\n"
            "No permite rastrear GPS privado, "
            "IP ni ubicación mediante ID "
            "o username.\n"
            "Una ubicación compartida no "
            "confirma la posición actual.\n\n"
            "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
        )

        await event.eor(ficha[:4000])

    except ValueError:
        await event.eor(
            "❌ Username o ID inválido "
            "o no accesible."
        )

    except RPCError as error:
        await event.eor(
            "❌ Error de Telegram: "
            + type(error).__name__
        )

    except Exception as error:
        await event.eor(
            "❌ Error: "
            + type(error).__name__
        )
