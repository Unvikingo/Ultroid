




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
            if (usuario.username or "").lower() == username.lower():
                entidad = usuario
                break

        if entidad is None:
            for canal in resultado.chats:
                if (getattr(canal, "username", None) or "").lower() == username.lower():
                    entidad = canal
                    break

        if entidad is None:
            return await event.eor(
                "❌ No se encontró un perfil con ese username."
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

        # Intentar enviar foto y ficha juntas
        try:
            foto = await event.client.download_profile_photo(
                entidad,
                file=bytes
            )

            if foto:
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

        # Si no hay foto accesible, enviar solo texto
        await event.eor(mensaje)

    except RPCError as error:
        await event.eor(
            f"❌ Error de Telegram: {type(error).__name__}"
        )

    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )


        # Buscar el usuario correspondiente
        usuario = next(
            (
                u for u in resultado.users
                if (u.username or "").lower() == username.lower()
            ),
            None
        )

        if usuario is None:
            if resultado.chats:
                return await event.eor(
                    "🔎 Ese username corresponde a un canal o grupo."
                )

            return await event.eor(
                "❌ No se encontró ese usuario."
            )

        if not isinstance(usuario, User):
            return await event.eor(
                "❌ La entidad encontrada no es un usuario."
            )

        nombre = " ".join(
            filter(None, [
                usuario.first_name,
                usuario.last_name
            ])
        ) or "No disponible"

        bio = "No disponible"

        try:
            completo = await event.client(
                GetFullUserRequest(usuario)
            )
            bio = completo.full_user.about or bio
        except RPCError:
            pass

        mensaje = (
            "⚔️ INVESTIGACIÓN DEL VALHALLA ⚔️\n\n"
            f"👤 Nombre: {nombre}\n"
            f"🆔 ID: {usuario.id}\n"
            f"🔗 Username: @{usuario.username}\n"
            f"🤖 Bot: {'Sí' if usuario.bot else 'No'}\n"
            f"📝 Biografía: {bio}\n\n"
            "🐺 ARCHIVOS DEL VIKINGO 🐺"
        )

        await event.eor(mensaje)

    except (ValueError, RPCError) as error:
        await event.eor(
            f"❌ Error de Telegram: {type(error).__name__}"
        )
    except Exception as error:
        await event.eor(
            f"❌ Error: {type(error).__name__}"
        )



