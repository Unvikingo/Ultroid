
import io
import re
from urllib.parse import urlparse

from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.errors import RPCError


REDES = {
    "instagram.com": "Instagram",
    "tiktok.com": "TikTok",
    "facebook.com": "Facebook",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "x.com": "X",
    "twitter.com": "X",
    "twitch.tv": "Twitch",
    "github.com": "GitHub",
    "linktr.ee": "Linktree",
    "discord.gg": "Discord",
    "discord.com": "Discord",
}


def valor_booleano(objeto, campo):
    valor = getattr(objeto, campo, None)

    if valor is True:
        return "Sí"
    if valor is False:
        return "No"

    return "No informado"


def obtener_redes(bio):
    encontrados = []
    urls = re.findall(
        r"https?://[^\s<>\"']+",
        bio or "",
        flags=re.IGNORECASE
    )

    for url in urls:
        url = url.rstrip(".,;!?)")
        dominio = (
            urlparse(url).hostname or ""
        ).lower().removeprefix("www.")

        nombre = "Sitio web"

        for sitio, etiqueta in REDES.items():
            if (
                dominio == sitio
                or dominio.endswith("." + sitio)
            ):
                nombre = etiqueta
                break

        linea = f"• {nombre}: {url}"

        if linea not in encontrados:
            encontrados.append(linea)

    return (
        "\n".join(encontrados[:8])
        if encontrados
        else "Sin enlaces publicados en la biografía"
    )


async def resolver(event, argumento):
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
        flags=re.IGNORECASE
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
        raise ValueError("Formato inválido")

    resultado = await cliente(
        ResolveUsernameRequest(username)
    )

    entidades = (
        list(resultado.users)
        + list(resultado.chats)
    )

    for entidad in entidades:
        encontrado = (
            getattr(entidad, "username", None)
            or ""
        )

        if encontrado.lower() == username.lower():
            return entidad

    return None


async def obtener_detalles(event, entidad):
    datos = {
        "bio": "Sin información pública",
        "bio_estado": "No publicada",
        "comunes": "No informado",
        "participantes": "No aplica",
        "fecha": "No disponible",
        "tipo": "Desconocido",
        "nombre": "No disponible",
        "premium": "No informado",
        "extra": []
    }

    if isinstance(entidad, User):
        datos["tipo"] = (
            "Bot" if entidad.bot else "Usuario"
        )

        datos["nombre"] = " ".join(
            filter(None, [
                entidad.first_name,
                entidad.last_name
            ])
        ) or "Sin nombre visible"

        datos["premium"] = (
            "No aplica"
            if entidad.bot
            else valor_booleano(entidad, "premium")
        )

        datos["extra"].append(
            "🤖 Es bot: "
            + valor_booleano(entidad, "bot")
        )

        datos["extra"].append(
            "🚫 Cuenta eliminada: "
            + valor_booleano(entidad, "deleted")
        )

        datos["extra"].append(
            "⚠️ Cuenta scam: "
            + valor_booleano(entidad, "scam")
        )

        datos["extra"].append(
            "⚠️ Cuenta fake: "
            + valor_booleano(entidad, "fake")
        )

        try:
            completo = await event.client(
                GetFullUserRequest(entidad)
            )

            bio = getattr(
                completo.full_user,
                "about",
                None
            )

            if bio:
                datos["bio"] = bio
                datos["bio_estado"] = "Visible"

            comunes = getattr(
                completo.full_user,
                "common_chats_count",
                None
            )

            if comunes is not None:
                datos["comunes"] = str(comunes)

        except RPCError as error:
            datos["bio_estado"] = (
                "Consulta limitada: "
                + type(error).__name__
            )

    elif isinstance(entidad, Channel):
        datos["tipo"] = (
            "Supergrupo"
            if entidad.megagroup
            else "Canal"
        )

        datos["nombre"] = entidad.title
        datos["premium"] = "No aplica"

        if getattr(entidad, "date", None):
            datos["fecha"] = (
                entidad.date.strftime("%d/%m/%Y")
                + " (fecha del objeto de Telegram)"
            )

        try:
            completo = await event.client(
                GetFullChannelRequest(entidad)
            )

            bio = getattr(
                completo.full_chat,
                "about",
                None
            )

            if bio:
                datos["bio"] = bio
                datos["bio_estado"] = "Visible"

            cantidad = getattr(
                completo.full_chat,
                "participants_count",
                None
            )

            if cantidad is not None:
                datos["participantes"] = str(cantidad)
            else:
                datos["participantes"] = (
                    "No informado"
                )

        except RPCError as error:
            datos["bio_estado"] = (
                "Consulta limitada: "
                + type(error).__name__
            )

    elif isinstance(entidad, Chat):
        datos["tipo"] = "Grupo básico"
        datos["nombre"] = entidad.title
        datos["premium"] = "No aplica"

        if getattr(entidad, "date", None):
            datos["fecha"] = (
                entidad.date.strftime("%d/%m/%Y")
                + " (fecha del objeto de Telegram)"
            )

        try:
            completo = await event.client(
                GetFullChatRequest(entidad.id)
            )

            bio = getattr(
                completo.full_chat,
                "about",
                None
            )

            if bio:
                datos["bio"] = bio
                datos["bio_estado"] = "Visible"

            cantidad = getattr(
                completo.full_chat,
                "participants_count",
                None
            )

            if cantidad is not None:
                datos["participantes"] = str(cantidad)
            else:
                datos["participantes"] = (
                    "No informado"
                )

        except RPCError as error:
            datos["bio_estado"] = (
                "Consulta limitada: "
                + type(error).__name__
            )

    return datos


async def estado_en_grupo(event, entidad):
    if not isinstance(entidad, User):
        return "No aplica a grupos/canales"

    try:
        chat = await event.get_chat()

        if not isinstance(chat, (Channel, Chat)):
            return "Ejecutado fuera de un grupo"

        if isinstance(chat, Channel):
            if not chat.megagroup:
                return "Ejecutado en un canal"

        permisos = await event.client.get_permissions(
            chat,
            entidad
        )

        if permisos.is_creator:
            return "Propietario"

        if permisos.is_admin:
            return "Administrador"

        if getattr(permisos, "is_banned", False):
            return "Baneado o restringido"

        return "Sin restricción visible"

    except RPCError:
        return "No verificable con estos permisos"

    except (ValueError, TypeError):
        return "Usuario no accesible en este grupo"


def construir_ficha(entidad, datos, moderacion):
    username = getattr(
        entidad,
        "username",
        None
    )

    usuario = (
        "@" + username
        if username
        else "Sin username público"
    )

    enlace = (
        "https://t.me/" + username
        if username
        else "Sin enlace público"
    )

    verificado = valor_booleano(
        entidad,
        "verified"
    )

    bio = datos["bio"][:650]
    redes = obtener_redes(datos["bio"])
    extra = "\n".join(datos["extra"])

    ficha = (
        "👑 INVESTIGADOR SUPREMO V2 👑\n"
        "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"

        "👤 IDENTIDAD\n"
        f"Nombre: {datos['nombre'][:100]}\n"
        f"ID: {entidad.id}\n"
        f"Username: {usuario}\n"
        f"Tipo: {datos['tipo']}\n"
        f"Verificado: {verificado}\n"
        f"Premium: {datos['premium']}\n"
        f"{extra}\n\n"

        "🛡️ MODERACIÓN\n"
        f"Grupo actual: {moderacion}\n"
        f"Chats comunes: {datos['comunes']}\n"
        f"Participantes: {datos['participantes']}\n\n"

        "📅 INFORMACIÓN ADICIONAL\n"
        f"Fecha visible: {datos['fecha']}\n"
        f"Enlace: {enlace}\n\n"

        "📝 BIOGRAFÍA\n"
        f"Estado: {datos['bio_estado']}\n"
        f"{bio}\n\n"

        "🌐 REDES PUBLICADAS\n"
        f"{redes[:500]}\n\n"

        "🔐 PRIVACIDAD\n"
        "Teléfono oculto: No consultable\n"
        "Denunciantes: No consultables\n"
        "Baneos globales: Sin registro universal\n"
        "Federaciones: Sin integración\n\n"

        "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
    )

    return ficha


@ultroid_cmd(pattern=r"supremo2(?:\s+(.+))?$")
async def investigador_supremo_v2(event):
    argumento = event.pattern_match.group(1)

    try:
        entidad = await resolver(
            event,
            argumento
        )

        if entidad is None:
            return await event.eor(
                "❌ No se encontró ese perfil."
            )

        datos = await obtener_detalles(
            event,
            entidad
        )

        moderacion = await estado_en_grupo(
            event,
            entidad
        )

        ficha = construir_ficha(
            entidad,
            datos,
            moderacion
        )

        # Las fotos con descripción tienen
        # un límite de caracteres en Telegram.
        # Si el informe es largo, se envía
        # como texto para no perder información.

        if len(ficha) <= 1000:
            try:
                foto_bytes = (
                    await event.client.download_profile_photo(
                        entidad,
                        file=bytes
                    )
                )

                if foto_bytes:
                    foto = io.BytesIO(foto_bytes)
                    foto.name = "supremo_v2.jpg"

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
            "❌ Telegram rechazó la consulta: "
            + type(error).__name__
        )

    except Exception as error:
        await event.eor(
            "❌ Error del addon: "
            + type(error).__name__
        )
