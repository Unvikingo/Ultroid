



from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import User
from telethon.errors import RPCError


@ultroid_cmd(pattern=r"investigar(?:\s+(.+))?$")
async def investigar(event):
    objetivo = event.pattern_match.group(1)

    if not objetivo:
        return await event.eor(
            "🔎 Uso: .investigar @usuario"
        )

    try:
        username = objetivo.strip().lstrip("@")

        if not username or " " in username:
            return await event.eor(
                "❌ Escribe un username válido."
            )

        # Resolver el username directamente en Telegram
        resultado = await event.client(
            ResolveUsernameRequest(username)
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



