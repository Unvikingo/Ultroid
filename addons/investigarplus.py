
import io

from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import User, Channel
from telethon.errors import RPCError


@ultroid_cmd(pattern=r"investigarplus(?:\s+(.+))?$")
async def investigarplus(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor(
            "🔎 Uso: .investigarplus @usuario"
        )

    username = objetivo.strip().lstrip("@")

    if not username or " " in username:
        return await event.eor(
            "❌ Escribe un username público válido."
        )

    try:
        resultado = await event.client(
            ResolveUsernameRequest(username)
        )

        entidad = next(
            (
                u for u in resultado.users
                if (u.username or "").lower() == username.lower()
            ),
            None
        )

        if entidad is None:
            entidad = next(
                (
                    c for c in resultado.chats
                    if (
                        getattr(c, "username", None) or ""
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
        fecha = "No disponible"

        if isinstance(entidad, User):
            nombre = " ".join(
                filter(None, [
                    entidad.first_name,
                    entidad.last_name
                ])
            ) or "No disponible"

            tipo = "Bot" if entidad.bot else "Usuario"
            premium = "Sí" if getattr(
                entidad, "premium", False
            ) else "No indicado"

            try:
                completo = await event.client(
                    GetFullUserRequest(entidad)
                )
                bio = completo.full_user.about or bio
            except RPCError:
                pass

        elif isinstance(entidad, Channel):
            nombre = entidad.title
            tipo = "Grupo" if entidad.megagroup else "Canal"
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
                "❌ Tipo de perfil no compatible."
            )

        verificado = (
            "Sí" if getattr(entidad, "verified", False)
            else "No"
        )

        mensaje = (
            "👑 INVESTIGADOR PLUS DEL VALHALLA 👑\n\n"
            f"👤 Nombre: {nombre}\n"
            f"🆔 ID: {entidad.id}\n"
            f"🔗 Username: @{entidad.username}\n"
            f"📂 Tipo: {tipo}\n"
            f"✅ Verificado: {verificado}\n"
            f"💎 Premium: {premium}\n"
            f"👥 Participantes: {participantes}\n"
            f"📅 Fecha del canal/grupo: {fecha}\n"
            f"📝 Biografía: {bio}\n"
            f"🌐 Enlace: https://t.me/{entidad.username}\n\n"
            "⚔️ ARCHIVOS SECRETOS DEL VALHALLA ⚔️"
        )

        try:
            foto_bytes = await event.client.download_profile_photo(
                entidad,
                file=bytes
            )

            if foto_bytes:
                foto = io.BytesIO(foto_bytes)
                foto.name = "perfil_valhalla.jpg"

                await event.client.send_file(
                    event.chat_id,
                    foto,
                    caption=mensaje,
                    force_document=False,
                    reply_to=event.id
                )
                await event.delete()
                return

        except (RPCError, ValueError, TypeError):
            pass

        await event.eor(mensaje)

    except RPCError as error:
        await event.eor(
            f"❌ Error de Telegram: {type(error).__name__}"
        )

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )
