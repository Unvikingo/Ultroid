
import io
import re
from urllib.parse import urlparse

from telethon.tl.types import User, Channel
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import (
    GetFullChannelRequest,
    GetParticipantRequest,
)
from telethon.errors import RPCError


def redes_publicas(bio):
    """Enlaces publicados en la biografía."""
    urls = re.findall(
        r"https?://[^\s<>\"]+",
        bio or "",
        flags=re.IGNORECASE
    )

    sitios = {
        "instagram.com": "Instagram",
        "tiktok.com": "TikTok",
        "facebook.com": "Facebook",
        "youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "x.com": "X",
        "twitter.com": "X",
        "twitch.tv": "Twitch",
        "github.com": "GitHub",
    }

    lineas = []

    for url in dict.fromkeys(urls):
        url = url.rstrip(".,;!?)")
        dominio = (
            urlparse(url).hostname or ""
        ).lower().removeprefix("www.")

        nombre = "Web"

        for sitio, etiqueta in sitios.items():
            if dominio == sitio or dominio.endswith(
                "." + sitio
            ):
                nombre = etiqueta
                break

        lineas.append(f"• {nombre}: {url}")

    return "\n".join(lineas[:5]) or "No publicados"


async def resolver_objetivo(event, texto):
    """Admite respuesta, username o ID accesible."""

    if not texto:
        respuesta = await event.get_reply_message()

        if not respuesta:
            return None

        return await respuesta.get_sender()

    texto = texto.strip()

    if texto.startswith("https://t.me/"):
        texto = texto.split("t.me/", 1)[1]
        texto = texto.split("/", 1)[0]

    if texto.lstrip("-").isdigit():
        return await event.client.get_entity(int(texto))

    username = texto.lstrip("@")

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{4,31}",
        username
    ):
        raise ValueError("Username inválido")

    resultado = await event.client(
        ResolveUsernameRequest(username)
    )

    entidades = (
        list(resultado.users)
        + list(resultado.chats)
    )

    return next(
        (
            item for item in entidades
            if (
                getattr(item, "username", None) or ""
            ).lower() == username.lower()
        ),
        None
    )


async def consultar_grupo_actual(event, entidad):
    """Estado accesible en el grupo donde se ejecuta."""

    chat = await event.get_chat()

    if not isinstance(entidad, User):
        return "No aplica"

    if not getattr(chat, "megagroup", False):
        return "Consultar desde un supergrupo"

    try:
        resultado = await event.client(
            GetParticipantRequest(
                channel=chat,
                participant=entidad
            )
        )

        participante = resultado.participant
        clase = type(participante).__name__

        if clase == "ChannelParticipantCreator":
            return "Propietario"

        if clase == "ChannelParticipantAdmin":
            return "Administrador"

        if clase == "ChannelParticipantBanned":
            derechos = getattr(
                participante, "banned_rights", None
            )

            if getattr(
                derechos, "view_messages", False
            ):
                return "Baneado"

            return "Restringido"

        if clase == "ChannelParticipantLeft":
            return "No es miembro"

        return "Miembro"

    except RPCError:
        return "No se pudo verificar"


@ultroid_cmd(pattern=r"supremo(?:\s+(.+))?$")
async def supremo_unificado(event):

    texto = event.pattern_match.group(1)

    if not texto and not event.is_reply:
        return await event.eor(
            "🔎 INVESTIGADOR SUPREMO\n\n"
            "Usos:\n"
            ".supremo @usuario\n"
            ".supremo 123456789\n"
            "O responde a un mensaje con .supremo"
        )

    try:
        entidad = await resolver_objetivo(
            event, texto
        )

        if entidad is None:
            return await event.eor(
                "❌ No se encontró el perfil."
            )

        bio = "No disponible"
        participantes = "No disponible"
        comunes = "No disponible"
        premium = "No indicado"
        fecha = "No disponible"
        moderacion = "No aplica"

        if isinstance(entidad, User):
            nombre = " ".join(
                filter(None, [
                    entidad.first_name,
                    entidad.last_name
                ])
            ) or "No disponible"

            tipo = "Bot" if entidad.bot else "Usuario"

            if entidad.bot:
                premium = "No aplica"
            elif getattr(entidad, "premium", False):
                premium = "Sí"

            try:
                completo = await event.client(
                    GetFullUserRequest(entidad)
                )

                bio = completo.full_user.about or bio

                cantidad = getattr(
                    completo.full_user,
                    "common_chats_count",
                    None
                )

                if cantidad is not None:
                    comunes = str(cantidad)

            except RPCError:
                pass

            moderacion = await consultar_grupo_actual(
                event, entidad
            )

        elif isinstance(entidad, Channel):
            nombre = entidad.title

            tipo = (
                "Grupo" if entidad.megagroup
                else "Canal"
            )

            premium = "No aplica"

            if getattr(entidad, "date", None):
                fecha = entidad.date.strftime(
                    "%d/%m/%Y"
                )

            try:
                completo = await event.client(
                    GetFullChannelRequest(entidad)
                )

                bio = completo.full_chat.about or bio

                cantidad = getattr(
                    completo.full_chat,
                    "participants_count",
                    None
                )

                if cantidad is not None:
                    participantes = str(cantidad)

            except RPCError:
                pass

        else:
            return await event.eor(
                "❌ Tipo de entidad no compatible."
            )

        username = getattr(
            entidad, "username", None
        )

        usuario_publico = (
            f"@{username}"
            if username
            else "No disponible"
        )

        enlace = (
            f"https://t.me/{username}"
            if username
            else "No disponible"
        )

        verificado = (
            "Sí"
            if getattr(entidad, "verified", False)
            else "No"
        )

        redes = redes_publicas(bio)

        ficha = (
            "👑 INVESTIGADOR SUPREMO 👑\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"
            f"👤 Nombre: {nombre[:80]}\n"
            f"🆔 ID: {entidad.id}\n"
            f"🔗 Username: {usuario_publico}\n"
            f"📂 Tipo: {tipo}\n"
            f"✅ Verificado: {verificado}\n"
            f"💎 Premium: {premium}\n\n"
            "🛡️ MODERACIÓN\n"
            f"🏛️ Grupo actual: {moderacion}\n"
            f"👥 Chats comunes: {comunes}\n"
            f"👥 Participantes: {participantes}\n"
            "🚫 Baneos globales: No consultables\n"
            "🌐 Federaciones: Sin integración\n\n"
            f"📅 Fecha visible: {fecha}\n"
            f"🌍 Telegram: {enlace}\n\n"
            f"📝 BIOGRAFÍA:\n{bio[:500]}\n\n"
            f"🔎 REDES PÚBLICAS:\n{redes[:500]}\n\n"
            "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
        )

        # Telegram limita los pies de foto.
        # Si la ficha es larga, enviarla como
        # un único mensaje de texto.
        if len(ficha) > 1000:
            return await event.eor(ficha)

        try:
            foto_bytes = (
                await event.client.download_profile_photo(
                    entidad,
                    file=bytes
                )
            )

            if foto_bytes:
                foto = io.BytesIO(foto_bytes)
                foto.name = "supremo_valhalla.jpg"

                await event.client.send_file(
                    event.chat_id,
                    foto,
                    caption=ficha,
                    force_document=False,
                    reply_to=event.reply_to_msg_id
                )

                await event.delete()
                return

        except (RPCError, ValueError, TypeError):
            pass

        await event.eor(ficha)

    except ValueError:
        await event.eor(
            "❌ Username o ID inválido, "
            "o no accesible para tu cuenta."
        )

    except RPCError as error:
        await event.eor(
            "❌ Telegram no pudo resolver "
            f"el perfil: {type(error).__name__}"
        )

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )











