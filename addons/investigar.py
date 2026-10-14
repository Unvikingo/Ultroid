





import io

from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import User, Channel
from telethon.errors import RPCError


@ultroid_cmd(pattern=r"investigar(?:\s+(.+))?$")
async def investigar(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor(
            "🔎 Uso: .investigar @usuario"
        )

    username = objetivo.strip().lstrip("@")

    if not username or " " in username:
        return await event.eor(
            "❌ Escribe un username válido."
        )

    try:
        resultado = await event.client(
            ResolveUsernameRequest(username)
        )

        entidad = None

        for usuario in resultado.users:
            if (
                (usuario.username or "").lower()
                == username.lower()
            ):
                entidad = usuario
                break

        if entidad is None:
            for canal in resultado.chats:
                canal_username = getattr(
                    canal, "username", None
                )

                if (
                    (canal_username or "").lower()
                    == username.lower()
                ):
                    entidad = canal
                    break

        if entidad is None:
            return await event.eor(
                "❌ No se encontró ese perfil."
            )

        bio = "No disponible"

        if isinstance(entidad, User):
            nombre = " ".join(
                filter(None, [
                    entidad.first_name,
                    entidad.last_name
                ])
            ) or "No disponible"

            tipo = "Bot" if entidad.bot else "Usuario"

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

            try:
                completo = await event.client(
                    GetFullChannelRequest(entidad)
                )
                bio = completo.full_chat.about or bio
            except RPCError:
                pass

        else:
            return await event.eor(
                "❌ Tipo de perfil no compatible."
            )

        mensaje = (
            "⚔️ INVESTIGACIÓN DEL VALHALLA ⚔️\n\n"
            f"👤 Nombre: {nombre}\n"
            f"🆔 ID: {entidad.id}\n"
            f"🔗 Username: @{entidad.username}\n"
            f"📂 Tipo: {tipo}\n"
            f"📝 Biografía: {bio}\n\n"
            "🐺 ARCHIVOS DEL VIKINGO 🐺"
        )

        # Descargar la foto accesible del perfil
        foto_bytes = None

        try:
            foto_bytes = await event.client.download_profile_photo(
                entidad,
                file=bytes
            )
        except (RPCError, ValueError, TypeError):
            pass

        # Enviar foto como imagen JPEG
        if foto_bytes:
            try:
                foto = io.BytesIO(foto_bytes)
                foto.name = "perfil.jpg"

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

        # Si no hay foto, enviar la ficha en texto
        await event.eor(mensaje)

    except RPCError as error:
        await event.eor(
            f"❌ Error de Telegram: {type(error).__name__}"
        )

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )




