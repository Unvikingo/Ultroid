
import io
import re
from urllib.parse import urlparse

from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import User, Channel
from telethon.errors import RPCError


def extraer_redes(texto):
    """Extrae enlaces publicados en la biografía."""
    if not texto:
        return "No se publicaron enlaces."

    enlaces = re.findall(
        r"https?://[^\s<>\"]+",
        texto,
        flags=re.IGNORECASE
    )

    dominios = {
        "instagram.com": "📸 Instagram",
        "tiktok.com": "🎵 TikTok",
        "facebook.com": "📘 Facebook",
        "youtube.com": "▶️ YouTube",
        "youtu.be": "▶️ YouTube",
        "x.com": "𝕏 X",
        "twitter.com": "𝕏 X",
        "twitch.tv": "🎮 Twitch",
        "github.com": "💻 GitHub",
    }

    encontrados = []
    vistos = set()

    for enlace in enlaces:
        enlace = enlace.rstrip(".,;!?)")

        if enlace in vistos:
            continue

        vistos.add(enlace)

        dominio = (
            urlparse(enlace).hostname or ""
        ).lower().removeprefix("www.")

        plataforma = "🌐 Página web"

        for sitio, nombre in dominios.items():
            if dominio == sitio or dominio.endswith("." + sitio):
                plataforma = nombre
                break

        encontrados.append(
            f"{plataforma}: {enlace}"
        )

    return (
        "\n".join(encontrados[:10])
        if encontrados
        else "No se publicaron enlaces."
    )


@ultroid_cmd(pattern=r"supremo(?:\s+(.+))?$")
async def investigador_supremo(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor(
            "🔎 Uso: .supremo @usuario"
        )

    username = objetivo.strip().lstrip("@")

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{4,31}",
        username
    ):
        return await event.eor(
            "❌ Escribe un username público válido."
        )

    try:
        resultado = await event.client(
            ResolveUsernameRequest(username)
        )

        entidades = (
            list(resultado.users)
            + list(resultado.chats)
        )

        entidad = next(
            (
                item for item in entidades
                if (
                    getattr(item, "username", None) or ""
                ).lower() == username.lower()
            ),
            None
        )

        if entidad is None:
            return await event.eor(
                "❌ No se encontró ese perfil público."
            )

        bio = "No disponible"
        participantes = "No disponible"
        premium = "No indicado"

        if isinstance(entidad, User):
            nombre = " ".join(
                filter(None, [
                    entidad.first_name,
                    entidad.last_name
                ])
            ) or "No disponible"

            tipo = (
                "Bot" if entidad.bot
                else "Usuario"
            )

            if not entidad.bot:
                premium = (
                    "Sí"
                    if getattr(entidad, "premium", False)
                    else "No indicado"
                )

            try:
                completo = await event.client(
                    GetFullUserRequest(entidad)
                )
                bio = completo.full_user.about or bio
            except RPCError:
                pass

        elif isinstance(entidad, Channel):
            nombre = entidad.title

            tipo = (
                "Grupo"
                if entidad.megagroup
                else "Canal"
            )

            premium = "No aplica"

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

        verificado = (
            "Sí"
            if getattr(entidad, "verified", False)
            else "No"
        )

        redes = extraer_redes(bio)

        # Limitar el texto para que quepa
        # en el pie de foto de Telegram.
        bio_corta = bio[:280]
        redes_cortas = redes[:300]

        ficha = (
            "👑 INVESTIGADOR SUPREMO 👑\n"
            "⚔️ ARCHIVOS DEL VALHALLA ⚔️\n\n"
            f"👤 Nombre: {nombre[:100]}\n"
            f"🆔 ID: {entidad.id}\n"
            f"🔗 Username: @{entidad.username}\n"
            f"📂 Tipo: {tipo}\n"
            f"✅ Verificado: {verificado}\n"
            f"💎 Premium: {premium}\n"
            f"👥 Participantes: {participantes}\n\n"
            f"📝 BIOGRAFÍA:\n{bio_corta}\n\n"
            f"🌐 REDES Y ENLACES PÚBLICOS:\n"
            f"{redes_cortas}\n\n"
            f"🔎 https://t.me/{entidad.username}\n\n"
            "🐺 EL VALHALLA TODO LO OBSERVA 🐺"
        )

        # Obtener la foto de perfil accesible
        foto_bytes = None

        try:
            foto_bytes = (
                await event.client.download_profile_photo(
                    entidad,
                    file=bytes
                )
            )
        except (RPCError, ValueError, TypeError):
            pass

        if foto_bytes:
            try:
                foto = io.BytesIO(foto_bytes)
                foto.name = "valhalla_perfil.jpg"

                await event.client.send_file(
                    event.chat_id,
                    foto,
                    caption=ficha[:1000],
                    force_document=False,
                    reply_to=event.id
                )

                await event.delete()
                return

            except (RPCError, ValueError, TypeError):
                pass

        await event.eor(ficha)

    except RPCError as error:
        await event.eor(
            "❌ Error de Telegram: "
            f"{type(error).__name__}"
        )

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )
